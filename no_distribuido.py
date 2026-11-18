"""
Simulação de sistema distribuído com TCP, threads, sincronização,
heartbeat, eleição de líder, simulação de falhas e coleta de métricas.

Execução:
    python no_distribuido.py

No Google Colab, coloque os arquivos do projeto na mesma pasta e execute:
    !python no_distribuido.py
"""

import json
import os
import socket
import threading
import time
from datetime import datetime

from GerenciadoHeartBeat import GerenciadoHeartBeat
from eleicao_lider import EleicaoLider
from simulador_falhas import SimuladorFalhas
from coletor_metricas import ColetorMetricas


ARQUIVO_CONFIG = "config.json"


def carregar_configuracao():
    with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def registrar_log(origem, mensagem, trava):
    with trava:
        horario = datetime.now().strftime("%H:%M:%S")
        print(f"{horario} [{origem}] {mensagem}", flush=True)


def enviar_mensagem(conexao, mensagem):
    """Envia uma mensagem JSON terminada em newline pelo socket TCP."""
    dados = json.dumps(mensagem, ensure_ascii=False) + "\n"
    conexao.sendall(dados.encode("utf-8"))


def executar_servidor(config, pronto, dados_compartilhados, trava_log,
                      metricas, simulador):
    host = config["host"]
    porta_configurada = config["porta"]
    quantidade = config["numero_clientes"]
    timeout = config["timeout_segundos"]

    conexoes = {}
    leitores = {}
    nos_ativos = set()
    lider = None
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((host, porta_configurada))
    servidor.listen(quantidade)
    servidor.settimeout(15)

    porta_real = servidor.getsockname()[1]
    dados_compartilhados["porta"] = porta_real
    registrar_log("SERVIDOR", f"Escutando em {host}:{porta_real}.", trava_log)
    pronto.set()

    try:
        # 1. Registro dos clientes
        while len(conexoes) < quantidade:
            conexao, endereco = servidor.accept()
            conexao.settimeout(timeout)
            leitor = conexao.makefile("r", encoding="utf-8")
            linha = leitor.readline()
            if not linha:
                conexao.close()
                continue

            registro = json.loads(linha)
            cliente_id = registro.get("cliente_id")
            if not cliente_id or cliente_id in conexoes:
                conexao.close()
                continue

            conexoes[cliente_id] = conexao
            leitores[cliente_id] = leitor
            nos_ativos.add(int(registro["numero"]))
            metricas.registrar_mensagem("REGISTRO")
            enviar_mensagem(conexao, {"tipo": "REGISTRO_CONFIRMADO"})
            registrar_log("SERVIDOR", f"{cliente_id} registrado a partir de {endereco}.", trava_log)

        # 2. Distribuição das tarefas
        tarefas = {
            "CLIENTE 1": [1, 2, 3],
            "CLIENTE 2": [4, 5, 6],
            "CLIENTE 3": [7, 8, 9]
        }
        resultados = {}

        for cliente_id, conexao in conexoes.items():
            enviar_mensagem(conexao, {
                "tipo": "TAREFA",
                "numeros": tarefas[cliente_id]
            })
            metricas.registrar_mensagem("TAREFA")
            registrar_log("SERVIDOR", f"Tarefa enviada para {cliente_id}: {tarefas[cliente_id]}.", trava_log)

        # 3. Recebimento dos resultados
        for cliente_id, conexao in conexoes.items():
            try:
                resposta = json.loads(leitores[cliente_id].readline())
                if resposta.get("tipo") == "RESULTADO":
                    resultados[cliente_id] = resposta["resultado"]
                    metricas.registrar_mensagem("RESULTADO")
                    registrar_log("SERVIDOR", f"Resultado de {cliente_id}: {resposta['resultado']}.", trava_log)
            except (socket.timeout, TimeoutError, OSError, json.JSONDecodeError) as erro:
                nos_ativos.discard(int(cliente_id.split()[-1]))
                registrar_log("SERVIDOR", f"Falha ao receber resultado de {cliente_id}: {erro}.", trava_log)

        estado_global = {
            "resultados_individuais": resultados,
            "resultado_global": sum(resultados.values())
        }
        registrar_log("SERVIDOR", f"Estado global calculado: {estado_global}.", trava_log)

        # 4. Sincronização e ACK
        for cliente_id in list(conexoes):
            numero = int(cliente_id.split()[-1])
            if numero in nos_ativos:
                enviar_mensagem(conexoes[cliente_id], {
                    "tipo": "SINCRONIZACAO",
                    "estado_global": estado_global
                })
                metricas.registrar_mensagem("SINCRONIZACAO")

        for cliente_id in list(conexoes):
            numero = int(cliente_id.split()[-1])
            if numero in nos_ativos:
                try:
                    ack = json.loads(leitores[cliente_id].readline())
                    if ack.get("tipo") == "ACK_SINCRONIZACAO":
                        metricas.registrar_mensagem("ACK_SINCRONIZACAO")
                        registrar_log("SERVIDOR", f"{cliente_id} confirmou a sincronização.", trava_log)
                except (socket.timeout, TimeoutError, OSError, json.JSONDecodeError) as erro:
                    nos_ativos.discard(numero)
                    registrar_log("SERVIDOR", f"{cliente_id} não confirmou a sincronização: {erro}.", trava_log)

        # 5. Heartbeat
        heartbeat = GerenciadoHeartBeat(timeout, lambda o, m: registrar_log(o, m, trava_log), metricas)
        for cliente_id in list(conexoes):
            numero = int(cliente_id.split()[-1])
            if numero not in nos_ativos:
                continue
            conexoes[cliente_id].settimeout(timeout)
            ativo = heartbeat.verificar_no(
                cliente_id, conexoes[cliente_id], leitores[cliente_id], enviar_mensagem
            )
            if not ativo:
                nos_ativos.discard(numero)

        # 6. Eleição de líder entre os nós que permaneceram ativos
        eleicao = EleicaoLider(lambda o, m: registrar_log(o, m, trava_log))
        lider = eleicao.eleger(nos_ativos)

        for cliente_id, conexao in conexoes.items():
            numero = int(cliente_id.split()[-1])
            if numero in nos_ativos:
                try:
                    enviar_mensagem(conexao, {
                        "tipo": "LIDER_ELEITO",
                        "lider": lider
                    })
                    metricas.registrar_mensagem("LIDER_ELEITO")
                except OSError:
                    nos_ativos.discard(numero)

        # 7. Encerramento
        for cliente_id, conexao in conexoes.items():
            try:
                enviar_mensagem(conexao, {"tipo": "ENCERRAR"})
            except OSError:
                pass

        registrar_log("SERVIDOR", f"Nós ativos ao final: {sorted(nos_ativos)}.", trava_log)
        metricas.finalizar(nos_ativos, lider)

    finally:
        for leitor in leitores.values():
            try:
                leitor.close()
            except OSError:
                pass
        for conexao in conexoes.values():
            try:
                conexao.close()
            except OSError:
                pass
        servidor.close()
        registrar_log("SERVIDOR", "Servidor encerrado.", trava_log)


def executar_cliente(numero, config, pronto, dados_compartilhados,
                     trava_log, simulador):
    cliente_id = f"CLIENTE {numero}"
    host = config["host"]
    timeout = config["timeout_segundos"]
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.settimeout(timeout + 5)
    leitor = None

    try:
        pronto.wait()
        porta = dados_compartilhados["porta"]
        cliente.connect((host, porta))
        leitor = cliente.makefile("r", encoding="utf-8")
        enviar_mensagem(cliente, {
            "tipo": "REGISTRO",
            "cliente_id": cliente_id,
            "numero": numero
        })
        resposta = json.loads(leitor.readline())
        registrar_log(cliente_id, f"Conectado e registrado: {resposta.get('tipo')}.", trava_log)

        # Recebe tarefa e devolve resultado
        tarefa = json.loads(leitor.readline())
        if tarefa.get("tipo") == "TAREFA":
            numeros = tarefa["numeros"]
            time.sleep(config["tempo_processamento"])
            resultado = sum(numeros)
            enviar_mensagem(cliente, {
                "tipo": "RESULTADO",
                "cliente_id": cliente_id,
                "resultado": resultado
            })
            registrar_log(cliente_id, f"Calculou {numeros}; resultado = {resultado}.", trava_log)

        # Recebe estado global e confirma
        sincronizacao = json.loads(leitor.readline())
        if sincronizacao.get("tipo") == "SINCRONIZACAO":
            registrar_log(cliente_id, f"Estado global recebido: {sincronizacao['estado_global']}.", trava_log)
            enviar_mensagem(cliente, {
                "tipo": "ACK_SINCRONIZACAO",
                "cliente_id": cliente_id
            })

        # Heartbeat: o simulador pode suprimir o PONG
        ping = json.loads(leitor.readline())
        if ping.get("tipo") == "PING":
            if simulador.deve_ignorar_ping(numero):
                registrar_log(cliente_id, "Falha simulada: PONG não será enviado.", trava_log)
                time.sleep(timeout + 1)
                return
            enviar_mensagem(cliente, {"tipo": "PONG", "cliente_id": cliente_id})
            registrar_log(cliente_id, "PING recebido; PONG enviado.", trava_log)

        # Recebe o resultado da eleição e encerramento
        proxima = json.loads(leitor.readline())
        if proxima.get("tipo") == "LIDER_ELEITO":
            registrar_log(cliente_id, f"Líder eleito: CLIENTE {proxima.get('lider')}.", trava_log)
            proxima = json.loads(leitor.readline())

        if proxima.get("tipo") == "ENCERRAR":
            registrar_log(cliente_id, "Encerramento recebido.", trava_log)

    except (socket.timeout, TimeoutError) as erro:
        registrar_log(cliente_id, f"Timeout: {erro}.", trava_log)
    except (ConnectionError, OSError, json.JSONDecodeError, KeyError) as erro:
        registrar_log(cliente_id, f"Erro de comunicação: {erro}.", trava_log)
    finally:
        if leitor is not None:
            try:
                leitor.close()
            except OSError:
                pass
        cliente.close()
        registrar_log(cliente_id, "Cliente finalizado.", trava_log)


def main():
    config = carregar_configuracao()
    diretorio = config["diretorio_evidencias"]
    os.makedirs(diretorio, exist_ok=True)

    trava_log = threading.Lock()
    pronto = threading.Event()
    dados_compartilhados = {}
    metricas = ColetorMetricas(diretorio)
    simulador = SimuladorFalhas(config.get("clientes_com_falha", []))

    registrar_log("SISTEMA", "Iniciando simulação distribuída.", trava_log)

    servidor_thread = threading.Thread(
        target=executar_servidor,
        args=(config, pronto, dados_compartilhados, trava_log, metricas, simulador),
        name="Thread-Servidor"
    )
    servidor_thread.start()
    pronto.wait()

    clientes_threads = []
    for numero in range(1, config["numero_clientes"] + 1):
        thread = threading.Thread(
            target=executar_cliente,
            args=(numero, config, pronto, dados_compartilhados, trava_log, simulador),
            name=f"Thread-Cliente-{numero}"
        )
        clientes_threads.append(thread)
        thread.start()

    for thread in clientes_threads:
        thread.join()
    servidor_thread.join()

    registrar_log("SISTEMA", "Simulação finalizada. Consulte a pasta evidencias/.", trava_log)


if __name__ == "__main__":
    main()

"""Gerenciamento de heartbeat (PING/PONG) dos nós clientes."""

import time
from socket import timeout as SocketTimeout


class GerenciadoHeartBeat:
    def __init__(self, timeout_segundos, registrar_log, coletor_metricas):
        self.timeout_segundos = timeout_segundos
        self.registrar_log = registrar_log
        self.metricas = coletor_metricas

    def verificar_no(self, cliente_id, conexao, leitor, enviar):
        """Envia PING e aguarda PONG. Retorna True se o nó estiver ativo."""
        inicio = time.perf_counter()
        try:
            enviar(conexao, {"tipo": "PING"})
            self.metricas.registrar_mensagem("PING")
            resposta = leitor.readline()
            if not resposta:
                raise ConnectionError("Conexão encerrada antes do PONG.")

            import json
            mensagem = json.loads(resposta)
            if mensagem.get("tipo") != "PONG":
                raise ValueError("Resposta inesperada ao PING.")

            duracao = time.perf_counter() - inicio
            self.metricas.registrar_mensagem("PONG")
            self.metricas.registrar_latencia(duracao)
            self.registrar_log("HEARTBEAT", f"{cliente_id} respondeu PONG em {duracao:.4f}s.")
            return True

        except (SocketTimeout, TimeoutError, ConnectionError, OSError, ValueError) as erro:
            duracao = time.perf_counter() - inicio
            self.metricas.registrar_falha(duracao)
            self.registrar_log(
                "HEARTBEAT",
                f"{cliente_id} considerado indisponível após {duracao:.4f}s: {erro}"
            )
            return False

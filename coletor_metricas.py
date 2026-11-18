"""Coleta e exportação de métricas da execução."""

import csv
import json
import os
import time


class ColetorMetricas:
    def __init__(self, diretorio):
        self.diretorio = diretorio
        os.makedirs(diretorio, exist_ok=True)
        self.inicio = time.perf_counter()
        self.mensagens = {}
        self.latencias = []
        self.falhas_detectadas = 0
        self.tempos_deteccao = []

    def registrar_mensagem(self, tipo):
        self.mensagens[tipo] = self.mensagens.get(tipo, 0) + 1

    def registrar_latencia(self, segundos):
        self.latencias.append(float(segundos))

    def registrar_falha(self, segundos):
        self.falhas_detectadas += 1
        self.tempos_deteccao.append(float(segundos))

    def finalizar(self, nos_ativos, lider):
        duracao = time.perf_counter() - self.inicio
        media_latencia = (
            sum(self.latencias) / len(self.latencias) if self.latencias else 0.0
        )
        dados = {
            "duracao_total_segundos": round(duracao, 4),
            "mensagens_por_tipo": self.mensagens,
            "total_mensagens_registradas": sum(self.mensagens.values()),
            "latencia_media_pong_segundos": round(media_latencia, 4),
            "falhas_detectadas": self.falhas_detectadas,
            "tempos_deteccao_falha_segundos": [
                round(x, 4) for x in self.tempos_deteccao
            ],
            "nos_ativos_ao_final": sorted(nos_ativos),
            "lider_eleito": lider
        }

        caminho_json = os.path.join(self.diretorio, "metricas.json")
        with open(caminho_json, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=4)

        caminho_csv = os.path.join(self.diretorio, "metricas.csv")
        with open(caminho_csv, "w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(["metrica", "valor"])
            escritor.writerow(["duracao_total_segundos", round(duracao, 4)])
            escritor.writerow(["total_mensagens_registradas", sum(self.mensagens.values())])
            escritor.writerow(["latencia_media_pong_segundos", round(media_latencia, 4)])
            escritor.writerow(["falhas_detectadas", self.falhas_detectadas])
            escritor.writerow(["nos_ativos_ao_final", ",".join(map(str, sorted(nos_ativos)))])
            escritor.writerow(["lider_eleito", lider if lider is not None else "nenhum"])

        return dados

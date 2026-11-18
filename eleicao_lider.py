"""Eleição de líder pelo algoritmo Bully, em uma simulação coordenada."""

class EleicaoLider:
    def __init__(self, registrar_log):
        self.registrar_log = registrar_log
        self.lider_atual = None

    def eleger(self, nos_ativos):
        """
        Simula o algoritmo Bully: o nó ativo de maior identificador vence.
        Cada nó ativo consulta os nós de identificador superior; se não houver
        nó superior ativo, ele se anuncia como líder.
        """
        ativos = sorted(set(nos_ativos))
        if not ativos:
            self.lider_atual = None
            self.registrar_log("ELEICAO", "Nenhum nó disponível para assumir a liderança.")
            return None

        for no in ativos:
            superiores = [outro for outro in ativos if outro > no]
            self.registrar_log(
                "ELEICAO",
                f"Nó {no} inicia eleição; nós de maior ID ativos: {superiores or 'nenhum'}."
            )
            if not superiores:
                self.lider_atual = no
                self.registrar_log("ELEICAO", f"Nó {no} anuncia-se como novo líder.")
                self.registrar_log("ELEICAO", f"Mensagem COORDINATOR: líder eleito = {no}.")
                return no

        return None

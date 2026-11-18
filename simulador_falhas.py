"""Cenários controlados para simulação de falhas."""

class SimuladorFalhas:
    def __init__(self, clientes_com_falha=None):
        self.clientes_com_falha = set(clientes_com_falha or [])

    def deve_ignorar_ping(self, numero_cliente):
        """Retorna True quando o cliente deve simular ausência de PONG."""
        return numero_cliente in self.clientes_com_falha

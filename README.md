# Projeto de Sistemas Distribuídos

## Arquivos
- `no_distribuido.py`: servidor coordenador, clientes, TCP, tarefas e sincronização.
- `GerenciadoHeartBeat.py`: verificação de disponibilidade por PING/PONG.
- `eleicao_lider.py`: simulação do algoritmo Bully entre os nós ativos.
- `simulador_falhas.py`: configuração dos nós que não responderão ao heartbeat.
- `coletor_metricas.py`: exportação de métricas em CSV e JSON.
- `config.json`: parâmetros da simulação.

## Execução
Coloque todos os arquivos na mesma pasta e execute:
```bash
python no_distribuido.py
```
No Google Colab, carregue os arquivos para o ambiente e execute:
```python
!python no_distribuido.py
```

## Cenário padrão
O Cliente 3 é configurado para não responder ao PING. O servidor deve detectar a indisponibilidade e realizar a eleição entre os clientes ativos. O Cliente 2 deve ser escolhido como líder, pois possui o maior identificador entre os nós ativos.

## Evidências
A execução cria `evidencias/metricas.json` e `evidencias/metricas.csv`.
Os arquivos de evidência devem ser gerados executando o programa; não use resultados esperados como se fossem resultados medidos.

## Observação técnica
A eleição Bully é simulada pelo coordenador usando a lista de nós que responderam ao heartbeat. A lógica de seleção segue o critério de maior identificador ativo, mas as mensagens de eleição não são trocadas diretamente em conexões peer-to-peer entre os clientes. Se a avaliação exigir eleição distribuída peer-to-peer, essa parte deverá ser ampliada.

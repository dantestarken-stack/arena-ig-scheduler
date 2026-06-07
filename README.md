# Arena IG Scheduler
Posta os stories recorrentes do @arenadogburger automaticamente (cron na nuvem).
- `schedule.json` — grade (dia/hora/story) TZ America/Sao_Paulo
- `publish.py run` — publica os stories devidos na janela atual (idempotente via posted-log.json)
- Secret necessário: `IG_TOKEN` (page token da Arena). IG_ID está no schedule.json.
Editar grade = editar schedule.json. Pausar = desabilitar o workflow.

# Fase 3 · integración operativa de givemotion

Una aplicación Python: guion → VisualStoryboard V2 → renderer nativo → FFprobe/decodificación → metadatos, calendario y publicador MOCK. Código de render de las entregas en c33ade2; rama base 46677de preservada.

| Trabajo | Motor | Duración / frames | Render s | CPU s | RSS árbol MiB | MiB MP4 |
|---|---|---|---|---|---|---|
| factory_givemotion | givemotion 0.1.6 | 40 s / 960 | 41.42 | 64.47 | 1125.41 | 1.662 |
| budget_regression_givemotion | givemotion 0.1.6 | 55 s / 1320 | 58.62 | 99.03 | 1134.69 | 2.086 |
| opportunity_hyperframes | hyperframes 0.9.59 | 40 s / 960 | 76.83 | 81.71 | 1490.88 | 1.126 |


Resultado: ciclo completo SIMULATED_DONE con un render y un registro remoto MOCK; 121 tests y Ruff PASS.

Evidencia completa local: `out/phase3/report.json`, `report.md`, `review.html`. Uso y pendientes TTS: [PHASE3_GIVEMOTION.md](PHASE3_GIVEMOTION.md). Componentes e inventario legado documentados. Ningún upload real, push, merge o despliegue. Los diez MP4 anteriores se verificaron por SHA-256 y la rama original permanece en 46677de.

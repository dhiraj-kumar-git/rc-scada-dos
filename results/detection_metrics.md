# Metrics (test split only)

Training windows: 71966, test windows: 89952. Exported rules agree with sklearn on 1.0000 of test windows.

## Per-window precision, recall, F1

| class | precision | recall | F1 | test windows |
| --- | --- | --- | --- | --- |
| normal | 1.000 | 0.999 | 0.999 | 82077 |
| ping_flood | 1.000 | 1.000 | 1.000 | 3091 |
| syn_flood | 0.999 | 1.000 | 0.999 | 3091 |
| modbus_flood | 0.933 | 0.978 | 0.955 | 1693 |

## Confusion matrix (rows = true, columns = predicted)

| | normal | ping_flood | syn_flood | modbus_flood |
| --- | --- | --- | --- | --- |
| normal | 81959 | 0 | 0 | 118 |
| ping_flood | 0 | 3091 | 0 | 0 |
| syn_flood | 1 | 0 | 3090 | 0 |
| modbus_flood | 33 | 0 | 4 | 1656 |

## Alarms per test capture (learned rules + 3-window persistence)

| capture | scenario | first attack window | first alarm window | delay (ms) | false alarm windows |
| --- | --- | --- | --- | --- | --- |
| clean_1h | normal | -1 | -1 | - | 0 |
| ping_5m_0p5h | ping_flood | 2986 | 2988 | 200 | 0 |
| syn_5m_0p5h | syn_flood | 2981 | 2984 | 300 | 0 |
| modbus_5m_0p5h | modbus_flood | 2987 | 2989 | 200 | 33 |

## Comparison: teammates' hand rule (modbus >= 8 for 3 windows)

| capture | scenario | first alarm window | delay (ms) | false alarm windows |
| --- | --- | --- | --- | --- |
| clean_1h | normal | -1 | - | 0 |
| modbus_5m_0p5h | modbus_flood | 2991 | 400 | 2 |

## DoS or DDoS: distinct-source estimate (T = 16.00, set_bits >= 16)

| capture | scenario | attack windows | attack windows flagged DDoS | normal windows | normal windows flagged DDoS | max estimate in attack windows |
| --- | --- | --- | --- | --- | --- | --- |
| clean_1h | normal | 0 | 0 | 35999 | 0 | - |
| ping_5m_0p5h | ping_flood | 3091 | 2948 | 14898 | 0 | 22.2 |
| syn_5m_0p5h | syn_flood | 3091 | 2942 | 14892 | 0 | 21.2 |
| modbus_5m_0p5h | modbus_flood | 1693 | 0 | 16288 | 0 | 3.0 |

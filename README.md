# taboun

taboun is a python chess-bot built on top of `python-chess`.

## bots

| Bot | File | Idea | Notes |
| --- | --- | --- | --- |
| `tabounV1` | `src/bot/tabounv1.py` | Random legal move | |
| `tabounV2` | `src/bot/tabounv2.py` | Minimax + material evaluation | Configurable depth (default `2`) |
| `tabounV3` | `src/bot/tabounv3.py` | Minimax + simplified evaluation | Better positional sense than V2 |
| `tabounV4` | `src/bot/tabounv4.py` | Alpha-beta + simplified evaluation | depth `3` |
| `tabounV5` | `src/bot/tabounv5.py` | Alpha-beta + simplified evaluation + move ordering | Captures then checks then quiet moves |
| `tabounV6` | `src/bot/tabounv6.py` | Alpha-beta + simplified evaluation + quiescence | Extends capture sequences |

## Requirements

- `python-chess`

Install dependencies :

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install python-chess
```

## cli

```bash
python src/main.py
```

You will be prompted for:

- **Start position**: new game or load from **FEN** or **PGN**
- **Mode**: `human vs bot` or `bot vs bot`
- **Bot**: pick from the available bots
- **Color** (human vs bot): play White or Black

During the game:

- Type moves in **SAN** (e.g. `e4`, `Nf3`, `O-O`) or **UCI** (e.g. `e2e4`, `g1f3`, `e7e8q`)
- Type `abandon` to resign
- The move list is printed in a chess-like format: `1. e4 e5 2. d4 d5 ...`

At the end:

- The result is printed with the winning bot name + color
- You can save the game as a **PGN** file

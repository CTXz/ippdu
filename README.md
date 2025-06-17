# ippdu - Command-line utility to control *0816 Smart PDU's

This repository provides a command-line utility for controlling Chinese 0816-series smart PDUs. These devices expose a web interface for outlet control. The CLI tool uses Playwright to trigger state changes (e.g., switching outlets on or off), and simple HTTP requests to retrieve the current status of each outlet.

## Example usage

List all sockets
```bash
ippdu -u USERNAME -p PASSWORD -H IP -l
```

Turn outlet #0 on
```bash
ippdu -u USERNAME -p PASSWORD -H IP -o 0 -s 1
```

Toggle outlet by name
```bash
ippdu -u USERNAME -p PASSWORD -H IP -o Socket-Name -s 0
```

## Disclaimer

LLM/AI tools were used in the creation of this utility. It is provided as-is, without any warranty or guarantee of functionality. Use at your own risk.

## Installation

### Docker (Recommended)

A docker image is available in the repository which comes with all dependencies pre-installed. You can build it with the following commands:

```bash
chmod +x ippdu.py
docker build -t ippdu .
```

A wrapper script is also available to run the docker image with the required parameters. You can use it as follows:

```bash
chmod +x ippdu
./ippdu -u USERNAME -p PASSWORD -H IP -l
```

If you wish to add the wrapper script to your PATH, you can do so by copying it to a directory in your PATH, for example:

```bash
sudo cp ippdu /usr/local/bin/
```

### Without Docker

If you prefer to run the utility without Docker, you can install the required dependencies manually. Make sure the following python dependencies are installed:

- Playwright
- requests
- beautifulsoup4

Note that playwright requires additional setup to install the necessary browser binaries. You can do this by running:

```bash
playwright install
```

Once the dependencies are installed, you can run the utility directly with:

```bash
./ippdu.py -u USERNAME -p PASSWORD -H IP -l
```

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

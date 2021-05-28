# 💸 Tranfer client command line tool

This is a simple demo crypto transfer CLI tool written in Python. It connects to an API to get quote and make transfer after confirmation

## Installation and running

This project can be deployed using docker. Make sure [it is installed](https://www.docker.com/products/docker-desktop) on your machine and see instructions below to use the tool.

## Using the API

You can run the client CLI app using the following command
```
    ./client.sh run <arguments>
```

This command takes the required arguments:

|Argument         |Description                                                           |
|-----------------|----------------------------------------------------------------------|
|Instrument       |Order instrument to use. Available instruments can be shown using `-i`|
|Quantity         |Quantity to trade                                                     |

Additionally this command takes optional arguments:

|Argument         |Command                 |Description                                |
|-----------------|------------------------|-------------------------------------------|
|Show instruments |`-i` (optional)         |Show all available order instruments       |
|Side             |`-s side`  (optional)   |Choose trading order side (`buy` or `sell`)|
|Log              |`-l file` (optional)    |Choose logging file name                   |
|Debug            |`-d` (optional)         |Enable advanced logging for debugging      |

Example:
```
    ./client.sh run BTCUSD.SPOT 1.5
```

## Other commands

You can run unit tests using the following command:

```
    ./client.sh test
```

Additionally you can clean the container using `./client.sh clean` or use a shell with `./client.sh shell`.

## Design notes

- This is a fairly minimal approach. The API simply requests a quote, and executes it if possible.
- Most of client and server side errors are caught to display a user friendly reason and how to solve them.
- The CLI screen displays an interactive countdown whilst waiting for order confirmation, using separate thread.
- The communication to the API is handled via a dedicated class. It's possible to use it in a python shell.
- Some unit tests are included, but coverage could be extended with more time.


## Possible extensions

- Commands to show balances only
- Check the desired order quantity falls into the risk limits, and reject the command before asking a quote with user friendly error (e.g showing what's the maximum quantity for the chosen instrument)
- Graphical user interface
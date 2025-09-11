# Snakeware
Snakeware is a app handler/game launcher.

## Running Snakeware
### Windows

1. Clone the repo: `git clone https://github.com/TheRealInkDevil/snakeware.git`
2. Run `sw.py`

### Linux
Snakeware can theoretically run on Linux, it has not been tested and support is not guaranteed.

1. Clone the repo: `git clone https://github.com/TheRealInkDevil/snakeware.git`
2. Run `sw.py`

## Dependencies
Snakeware expects [gbe-fork](https://github.com/Detanup01/gbe_fork) and [Steamless](https://github.com/atom0s/Steamless) to be present. It can run without them, but issues might occur when they are not.

### gbe-fork
1. Download the latest release of gbe-fork from [here](https://github.com/Detanup01/gbe_fork/releases/latest)
2. Extract contents of `release` folder from downloaded archive into folder `sbe`

### Steamless
1. Download the latest release of Steamless from [here](https://github.com/atom0s/Steamless/releases/latest)
2. Extract into folder `steamless`

## TODO
- Implement installing and removing swapps
- Move the builtin swapps to their own repos
- Allow apps to have code entrypoints
- Completely decouple gbe-fork and Steamless
- Add a good update system
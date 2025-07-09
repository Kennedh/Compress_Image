#!/bin/bash

python3 main.py img.jpeg img_reduzida.jpeg \
  --max-width 1280 \
  --max-height 720 \
  --max-size-kb 30 \
  --quality 100 \
  --jpeg \
  --redim
  
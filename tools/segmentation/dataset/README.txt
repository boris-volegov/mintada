Dataset structure:
  images/  -> RGB images
  masks/   -> single-channel PNGs, 0=background, 1..K=classes
  train.txt, val.txt -> basenames (without extension) for each split

Tip: in PyTorch, load mask with PIL (mode 'L') and use as LongTensor.

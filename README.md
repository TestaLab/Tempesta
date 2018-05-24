Tempesta
=========
Measurement control and analysis for optical microscopy. Adaptation from Fede Barabas' Tormenta software https://github.com/fedebarabas/Tormenta


Contributors
------------

 - Andreas Bodén
 - Aurelién Barbotin
 - Federico Barabas
 - Jonatan Alvelid
 - Luciano Masullo
 - Shusei Masuda
 - Xavier Casas Moreno


Installation
------------

 - Download wheel file `tifffile-2017.5.23-cp35-cp35m-win_amd64.whl` from https://www.lfd.uci.edu/~gohlke/pythonlibs/

 - Install dependencies with pip
 
```
pip install nidaqmx git+https://github.com/fedebarabas/lantz opencv-python instrumental-lib  tifffile-2017.5.23-cp35-cp35m-win_amd64.whl
```

 - Copy `hamamatsu` folder from the repository to `$PYTHONFOLDER\Lib\site-packages\lantz\drivers\hamamatsu`

How to cite
-----------

If you used the code/program for your paper, please cite

Barabas et al., *Note: Tormenta: An open source Python-powered control software for camera based optical microscopy*, Review of Scientific Instruments, 2016.

https://doi.org/10.1063/1.4972392
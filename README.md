# TPK2GPKG

Takes either an Esri TPKX or VTPK file and converts it into Geopackage. To make it complicated Esri also has a format called TPK, but this is not supported. For VTPK the MVT extension for Geopackage is used, but if your VTPK is in google maps compatable tiles, you should be able to change the filename of the generated file to mbtiles and it should work in QGIS/GDAL.

I'm not a python programmer, so the code is far from perfect, but it works. 

Some information needed for tiling schemes / vector tiles, in Geopackage is not available in the Esri files, but the code makes due with what is available.

## Usage

You should be able to run:

```
python .\TPK2GPKG.py filename
```

Or just run the python script and it will ask for the file to convert.

Output is saved as ORIGINALNAME.ORIGINALEXTENSION.GPKG

## License

BSD-2-Clause License

Buy me beer, host my website, or other gifts if you like it.


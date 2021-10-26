# It might not look like yummy code, but it works, provided as is, MIT-license etc.
# Geopackage mvt extension https://gitlab.com/imagemattersllc/ogc-vtp2/-/blob/master/extensions/1-vte.adoc
# Esri compact cache specification https://github.com/Esri/raster-tiles-compactcache
# Esri tile cace specification https://github.com/Esri/tile-package-spec
import argparse
from os.path import exists
from zipfile import ZipFile
import sqlite3
import json
print("Made by Måns, buy him beer.")


class FilenameAction(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        self.validate(parser, value)
        setattr(namespace, self.dest, value)

    @staticmethod
    def validate(parser, value):
        if not exists(value):
        #if value not in ('foo', 'bar'):
            parser.error('{} does not exist'.format(value))

# Parse input arguments
parser = argparse.ArgumentParser()
parser.add_argument('--file_name', action=FilenameAction)
args = parser.parse_args()
if args.file_name is None:
    args.file_name = input('The TPKX or VTPK file you want to convert to Geopackage: ')
    FilenameAction.validate(parser, args.file_name)
#file_name = "C:/Users/mbc/Desktop/TPK/googlemaps.vtpk"
file_name = args.file_name

minLOD = 0
maxLOD = 0

con = sqlite3.connect(file_name + '.gpkg')
cur = con.cursor()

cur.execute("CREATE TABLE gpkg_geometry_columns (table_name TEXT NOT NULL,column_name TEXT NOT NULL,geometry_type_name TEXT NOT NULL,srs_id INTEGER NOT NULL,z TINYINT NOT NULL,m TINYINT NOT NULL,CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),CONSTRAINT uk_gc_table_name UNIQUE (table_name),CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id))")
cur.execute("CREATE TABLE gpkg_ogr_contents(table_name TEXT NOT NULL PRIMARY KEY,feature_count INTEGER DEFAULT NULL)")
cur.execute("CREATE TABLE gpkg_spatial_ref_sys (srs_name TEXT NOT NULL,srs_id INTEGER NOT NULL PRIMARY KEY,organization TEXT NOT NULL,organization_coordsys_id INTEGER NOT NULL,definition  TEXT NOT NULL,description TEXT)")
# You will have to add definitions for different projections here if you use other than 4326 or 3857
cur.execute("INSERT INTO gpkg_spatial_ref_sys (\"srs_name\", \"srs_id\", \"organization\", \"organization_coordsys_id\", \"definition\", \"description\") VALUES ('Undefined cartesian SRS', '-1', 'NONE', '-1', 'undefined', 'undefined cartesian coordinate reference system');")
cur.execute("INSERT INTO gpkg_spatial_ref_sys (\"srs_name\", \"srs_id\", \"organization\", \"organization_coordsys_id\", \"definition\", \"description\") VALUES ('Undefined geographic SRS', '0', 'NONE', '0', 'undefined', 'undefined geographic coordinate reference system');")
cur.execute("INSERT INTO gpkg_spatial_ref_sys (\"srs_name\", \"srs_id\", \"organization\", \"organization_coordsys_id\", \"definition\", \"description\") VALUES ('WGS 84 / Pseudo-Mercator', '3857', 'EPSG', '3857', 'PROJCS[\"WGS 84 / Pseudo-Mercator\",GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY[\"EPSG\",\"7030\"]],AUTHORITY[\"EPSG\",\"6326\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4326\"]],PROJECTION[\"Mercator_1SP\"],PARAMETER[\"central_meridian\",0],PARAMETER[\"scale_factor\",1],PARAMETER[\"false_easting\",0],PARAMETER[\"false_northing\",0],UNIT[\"metre\",1,AUTHORITY[\"EPSG\",\"9001\"]],AXIS[\"Easting\",EAST],AXIS[\"Northing\",NORTH],EXTENSION[\"PROJ4\",\"+proj=merc +a=6378137 +b=6378137 +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +k=1 +units=m +nadgrids=@null +wktext +no_defs\"],AUTHORITY[\"EPSG\",\"3857\"]]', '');")
cur.execute("INSERT INTO gpkg_spatial_ref_sys (\"srs_name\", \"srs_id\", \"organization\", \"organization_coordsys_id\", \"definition\", \"description\") VALUES ('WGS 84 geodetic', '4326', 'EPSG', '4326', 'GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY[\"EPSG\",\"7030\"]],AUTHORITY[\"EPSG\",\"6326\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AXIS[\"Latitude\",NORTH],AXIS[\"Longitude\",EAST],AUTHORITY[\"EPSG\",\"4326\"]]', 'longitude/latitude coordinates in decimal degrees on the WGS 84 spheroid');")

def readIndex(f):
    M = 2^40
    IDX = []
    for row in range(0, 128):
        for col in range(0, 128):
            TileOffset = int.from_bytes(f.read(5), "little")
            TileSize = int.from_bytes(f.read(3), "little")
            IDX.append(
                {'row': row, 
                'col': col,
                'tileOffset': TileOffset, 
                'tileSize': TileSize})
    return IDX

# opening the zip file in READ mode
with ZipFile(file_name, 'r') as zip:
    tilesType = 'tiles'
    if 'p12/root.json' in zip.namelist():
        tilesType = 'vector-tiles'
        print('Looks like a VTPK, will convert it...')
        root = zip.open('p12/root.json', 'r')
        root = json.load(root)
    if 'root.json' in zip.namelist():
        print('Looks like a TPKX, will convert it...')
        root = zip.open('root.json', 'r')
        root = json.load(root)
        package_name = root['name']
    # Create tiles table

    cur.execute("CREATE TABLE '{package_name}' (id INTEGER PRIMARY KEY AUTOINCREMENT,zoom_level INTEGER NOT NULL,tile_column INTEGER NOT NULL,tile_row INTEGER NOT NULL,tile_data BLOB NOT NULL,UNIQUE (zoom_level, tile_column, tile_row))")

    for i in zip.infolist():
        if not i.is_dir() and i.filename.endswith('.bundle'):
            #print(i.filename)
            f = i.filename.split('/')
            level = int(f[len(f)-2][1:])
            if level < minLOD:
                minLOD = level
            if level > maxLOD:
                maxLOD = level
            baseRow = int(f[len(f)-1][1:5],16)
            baseCol = int(f[len(f)-1][6:10],16)
            #print('level:',level) 
            #print('baseRow:',baseRow) 
            #print('baseCol:',baseCol) 
            

            with zip.open((i.filename), 'r') as f:
                version = int.from_bytes(f.read(4), "little")
                #print('version: ',version)
                recordCount = int.from_bytes(f.read(4), "little")
                #print('recordCount: ',recordCount)
                maxTileSize = int.from_bytes(f.read(4), "little")
                #print('maxTileSize: ',maxTileSize)
                offsetByteCount = int.from_bytes(f.read(4), "little")
                #print('offsetByteCount: ',offsetByteCount)
                slackSpace = int.from_bytes(f.read(8), "little")
                #print(slackSpace)
                fileSize = int.from_bytes(f.read(8), "little")
                #print('fileSize: ',fileSize)
                userHeaderOffset = int.from_bytes(f.read(8), "little")
                #print('userHeaderOffset: ',userHeaderOffset)
                userHeaderSize = int.from_bytes(f.read(4), "little")
                #print('userHeaderSize: ',userHeaderSize)
                legacy1 = int.from_bytes(f.read(4), "little")
                #print(legacy1)
                legacy2 = int.from_bytes(f.read(4), "little")
                #print(legacy2)
                legacy3 = int.from_bytes(f.read(4), "little")
                #print(legacy3)
                legacy4 = int.from_bytes(f.read(4), "little")
                #print(legacy4)
                indexSize = int.from_bytes(f.read(4), "little")
                #print('indexSize: ',indexSize)
               
                IDX = readIndex(f)
                for i in IDX:
                    if i['tileSize'] > 0:
                        #print(i)
                        f.seek(i['tileOffset'])   
                        ablob = f.read(i['tileSize'])
                        cur.execute("INSERT INTO '{package_name}' (zoom_level, tile_column, tile_row, tile_data) VALUES(?,?,?,?)",( level, baseCol+i['col'], baseRow+i['row'], sqlite3.Binary(ablob)))
                con.commit()

cur.execute("CREATE TABLE gpkg_contents (table_name TEXT NOT NULL PRIMARY KEY,data_type TEXT NOT NULL,identifier TEXT UNIQUE,description TEXT DEFAULT '',last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),min_x DOUBLE, min_y DOUBLE,max_x DOUBLE, max_y DOUBLE,srs_id INTEGER,CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id))")
# Yeah, this is not correct, but it looks like it works in most software, push if you find a better way to do it.
cur.execute("INSERT INTO 'gpkg_contents' VALUES (?, ?, 'identifier', 'description', (SELECT strftime('%Y-%m-%dT%H:%M:%fZ','now')), ?, ?, ?, ?, ?)",(package_name,tilesType,root['fullExtent']['xmin'],root['fullExtent']['ymin'],root['fullExtent']['xmax'],root['fullExtent']['ymax'],root['tileInfo']['spatialReference']['latestWkid']))

# TODO check that matrix set are correct
cur.execute("CREATE TABLE gpkg_tile_matrix_set (table_name TEXT NOT NULL PRIMARY KEY,srs_id INTEGER NOT NULL,min_x DOUBLE NOT NULL,min_y DOUBLE NOT NULL,max_x DOUBLE NOT NULL,max_y DOUBLE NOT NULL,CONSTRAINT fk_gtms_table_name FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),CONSTRAINT fk_gtms_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id))")
# Yeah, this is not correct, but it looks like it works in most software, push if you find a better way to do it.
cur.execute("INSERT INTO 'gpkg_tile_matrix_set' VALUES (?, ?, ?, ?, ?, ?)",(package_name,root['tileInfo']['spatialReference']['latestWkid'],root['tileInfo']['origin']['x'],root['fullExtent']['ymin'],root['fullExtent']['xmax'],root['tileInfo']['origin']['y']))

cur.execute("CREATE TABLE gpkg_tile_matrix (table_name TEXT NOT NULL,zoom_level INTEGER NOT NULL,matrix_width INTEGER NOT NULL,matrix_height INTEGER NOT NULL,tile_width INTEGER NOT NULL,tile_height INTEGER NOT NULL,pixel_x_size DOUBLE NOT NULL,pixel_y_size DOUBLE NOT NULL,CONSTRAINT pk_ttm PRIMARY KEY (table_name, zoom_level),CONSTRAINT fk_tmm_table_name FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name))")
for i in range(minLOD,maxLOD):
    cur.execute("INSERT INTO gpkg_tile_matrix VALUES(?,?,?,?,?,?,?,?)",(package_name,i,pow(2,i),pow(2,i),root['tileInfo']['cols'],root['tileInfo']['rows'],root['tileInfo']['lods'][i]['resolution'],root['tileInfo']['lods'][i]['resolution']))

if tilesType == 'vector-tiles':
    cur.execute("CREATE TABLE gpkg_extensions (   table_name TEXT,   column_name TEXT,   extension_name TEXT NOT NULL,   definition TEXT NOT NULL,   scope TEXT NOT NULL,   CONSTRAINT ge_tce UNIQUE (table_name, column_name, extension_name))")
    cur.execute("INSERT INTO gpkg_extensions (table_name, column_name, extension_name, definition, scope) VALUES ('gpkgext_vt_layers', '', 'im_vector_tiles', 'https://docs.opengeospatial.org/per/18-074.html#VectorTilesExtensionClause', 'read-write');")
    cur.execute("INSERT INTO gpkg_extensions (table_name, column_name, extension_name, definition, scope) VALUES ('gpkgext_vt_fields', '', 'im_vector_tiles', 'https://docs.opengeospatial.org/per/18-074.html#VectorTilesExtensionClause', 'read-write');")
    cur.execute("INSERT INTO gpkg_extensions (table_name, column_name, extension_name, definition, scope) VALUES ('{package_name}', 'tile_data', 'im_vector_tiles_mapbox', 'https://docs.opengeospatial.org/per/18-074.html#MapboxVectorTilesExtensionClause', 'read-write');")

    cur.execute("CREATE TABLE gpkgext_vt_fields (   id INTEGER CONSTRAINT vtf_pk PRIMARY KEY ASC NOT NULL UNIQUE,   layer_id INTEGER NOT NULL,   name TEXT NOT NULL,   type TEXT NOT NULL DEFAULT 'String',   CONSTRAINT fk_gvl_i FOREIGN KEY (layer_id) REFERENCES gpkgext_vt_layers(id))")
    #TODO insert something in this table
    #cur.execute("")
    cur.execute("CREATE TABLE gpkgext_vt_layers (  id INTEGER CONSTRAINT vtl_pk PRIMARY KEY ASC NOT NULL UNIQUE,  table_name TEXT NOT NULL,  name TEXT NOT NULL,  description TEXT,  minzoom INTEGER,  maxzoom INTEGER)")
    #TODO insert something in this table
    #cur.execute("")
    cur.execute("")

    #Make it MBTILES Compatable if webmercator
    cur.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('name', '{package_name}');")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('description', '');")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('type', 'baselayer');")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('version', '1');")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('format', 'pbf');")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('format_arguments', '');")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('minzoom', '{minLOD}');")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('maxzoom', '{maxLOD}');")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('scale', '1.000000');")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('profile', 'mercator');")
    cur.execute("INSERT INTO metadata (name, value) VALUES ('scheme', 'tms');")
    # This JSON needs to be improved, but we don't have the data in the VTPK file.... 
    cur.execute("INSERT INTO metadata (name, value) VALUES ('json', '{\"vector_layers\":[{\"id\":\"land20y\",\"description\":\"\",\"minzoom\":0, \"maxzoom\":5,\"fields\":{\"KKOD\":\"String\"}}]}');")

    cur.execute("CREATE VIEW tiles AS SELECT {package_name}.zoom_level, tile_column, tm.matrix_height-1-tile_row AS tile_row, tile_data FROM {package_name} JOIN gpkg_tile_matrix tm ON {package_name}.zoom_level = tm.zoom_level AND tm.table_name = '{package_name}'")

con.commit()
con.close()

print('Saved converted file as: '+file_name + '.gpkg')

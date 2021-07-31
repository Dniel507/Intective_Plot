import psycopg2
import geopandas
import pandas as pd
import bokeh
from bokeh.layouts import gridplot, grid,layout,column
from bokeh.plotting import figure, output_file, save, show, gmap
from bokeh.models import ColumnDataSource, HoverTool,Panel,Tabs, LogColorMapper, MultiPolygons, GMapOptions,BoxAnnotation,Toggle
from bokeh.palettes import RdYlBu11 as palette

color_mapper = LogColorMapper(palette=palette)
#----------------------------------------------------------  Functions  ---------------------------------------------------------

def getPointCoords(row, geom, coord_type):
    """Calculates coordinates ('x' or 'y') of a Point geometry"""
    if coord_type == 'x':
        return row[geom].x
    elif coord_type == 'y':
        return row[geom].y

def getPolyCoords(row, geom, coord_type):
    """Returns the coordinates ('x' or 'y') of edges of a Polygon exterior"""

    # Parse the exterior of the coordinate
    exterior = row[geom].exterior

    if coord_type == 'x':
        # Get the x coordinates of the exterior
        return list( exterior.coords.xy[0] )
    elif coord_type == 'y':
        # Get the y coordinates of the exterior
        return list( exterior.coords.xy[1] )

def multiGeomHandler(multi_geometry, coord_type, geom_type):
    """
    Function for handling multi-geometries. Can be MultiPoint, MultiLineString or MultiPolygon.
    Returns a list of coordinates where all parts of Multi-geometries are merged into a single list.
    Individual geometries are separated with np.nan which is how Bokeh wants them.
    # Bokeh documentation regarding the Multi-geometry issues can be found here (it is an open issue)
    # https://github.com/bokeh/bokeh/issues/2321
    """

    for i, part in enumerate(multi_geometry):
        # On the first part of the Multi-geometry initialize the coord_array (np.array)
        if i == 0:
            if geom_type == "MultiPoint":
                coord_arrays = np.append(getPointCoords(part, coord_type), np.nan)
            elif geom_type == "MultiLineString":
                coord_arrays = np.append(getLineCoords(part, coord_type), np.nan)
            elif geom_type == "MultiPolygon":
                coord_arrays = np.append(getPolyCoords(part, coord_type), np.nan)
        else:
            if geom_type == "MultiPoint":
                coord_arrays = np.concatenate([coord_arrays, np.append(getPointCoords(part, coord_type), np.nan)])
            elif geom_type == "MultiLineString":
                coord_arrays = np.concatenate([coord_arrays, np.append(getLineCoords(part, coord_type), np.nan)])
            elif geom_type == "MultiPolygon":
                coord_arrays = np.concatenate([coord_arrays, np.append(getPolyCoords(part, coord_type), np.nan)])

    # Return the coordinates
    return coord_arrays
#---------------------------------------------------------- CENTRO DE VACUNACION ----------------------------------------------------------
conn = psycopg2.connect(database = "postgres", user = "postgres", password = "123456",host = "ec2-3-132-216-22.us-east-2.compute.amazonaws.com",port = "5432")
points = geopandas.GeoDataFrame.from_postgis("SELECT * FROM ubicacion_escuelas WHERE gid <> 3269",conn,geom_col='geom')

#---------------------------------------------------------- EXTRACCION DE VARIABLES X Y
points['x'] = points.apply(getPointCoords,geom='geom',coord_type='x',axis=1)
points['y'] = points.apply(getPointCoords,geom='geom',coord_type='y',axis=1)
p_df = points.drop('geom',axis=1).copy()
p_source = ColumnDataSource(p_df)

#---------------------------------------------------------- CREACION DE VARIABLE MAPA
output_file("pan_map.html")

#---------------------------------------------------------- TOOPTIP HOVER
cdb_hover = HoverTool()
cdb_hover.tooltips = [('Address of the point', '@nombre')]

edc_hover = HoverTool()
edc_hover.tooltips = [('Provincia', '@provincia'),
                      ('Corregimiento', '@corregimie'),
                      ('Casos', '@cantidad'),
                      ('Hospitalizados', '@hospitaliz'),
                      ('Recuperados', '@recuperado'),
                      ('Fallecidos', '@fallecido'),]

#---------------------------------------------------------- Map Options
cdv_map = GMapOptions(lat=8.9824, lng=-79.5199, map_type="roadmap",zoom=7)
edc_map = GMapOptions(lat=8.9824, lng=-79.5199, map_type="roadmap",zoom=7)

#---------------------------------------------------------- Plot : CENTROS DE VACUNACION
cdv = gmap("AIzaSyBmG4umB0ThuiwtDxhNhzx2nJ0lVX4r_44", cdv_map, title="Centros de Vacunacion")
cdv.circle('x','y', size=5, source=p_source, color="blue")
cdv.add_tools(cdb_hover)

#---------------------------------------------------------- ESTADO DE COVID ----------------------------------------------------------
conn2 = psycopg2.connect(database = "cdv2021", user = "postgres", password = "2021",host = "localhost",port = "5432")
c_pa = geopandas.GeoDataFrame.from_postgis("SELECT * FROM corregimientos__pu_",conn2,geom_col='geom')

c_pa['x'] = c_pa.apply(getPointCoords,geom='geom',coord_type='x',axis=1)
c_pa['y'] = c_pa.apply(getPointCoords,geom='geom',coord_type='y',axis=1)

c_df = c_pa.drop('geom',axis=1).copy()
c_source = ColumnDataSource(c_df)

edc = gmap("AIzaSyBmG4umB0ThuiwtDxhNhzx2nJ0lVX4r_44", edc_map, title="Status de Covid en Panama")
edc.circle('x','y', size=5, source=c_source, color="red")
edc.add_tools(edc_hover)

#---------------------------------------------------------- QUERY 1 ----------------------------------------------------------

query1 = pd.read_sql_query("SELECT provincia, count(*) as escuelas FROM ubicacion_escuelas WHERE nombre like 'Escuela%' Group by provincia",conn)
query2 = pd.read_sql_query("SELECT provincia, sum(cantidad) as casos_de_covid FROM corregimientos__pu_ Group by provincia  ",conn2)

df = pd.DataFrame(query1)
provincias = df['provincia']
escuelas =df['escuelas']

df2 = pd.DataFrame(query2)
p2 = df2['provincia']
cc = df2['casos_de_covid']


b1= figure(y_range=provincias,  plot_width=500, plot_height=500, x_axis_label="Escuelas",title="Centros por Provincias")
b1.hbar(y=provincias, right=escuelas,left=0,height=0.4,color="orange",fill_alpha=0.5)

b2= figure(y_range=p2,  plot_width=500, plot_height=500, x_axis_label="Casos de covid",title="Casos de Covid")
b2.hbar(y=p2, right=cc,left=0,height=0.4,color="orange",fill_alpha=0.5)

l1 = layout(
    [[b1]],
    [ [cdv] ],
    [ [edc] ],
    sizing_mode='stretch_width'
)

l2 = layout(
    [ [b2] ],
    [ [cdv] ],
    [ [edc] ],
    sizing_mode='stretch_width'
)

tab1 = Panel(child=l1, title="Centros por Provincias")
tab2 = Panel(child=l2, title="Casos de Covid")

show(Tabs(tabs=[ tab1, tab2 ]))



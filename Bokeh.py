import psycopg2
import geopandas
import pandas as pd
import bokeh
from bokeh.layouts import gridplot
from bokeh.plotting import figure, output_file, save, show, gmap
from bokeh.models import ColumnDataSource, HoverTool, LogColorMapper, MultiPolygons, GMapOptions
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
conn = psycopg2.connect(database = "postgres", user = "postgres", password = "123456",host = "ec2-3-17-190-194.us-east-2.compute.amazonaws.com",port = "5432")
points = geopandas.GeoDataFrame.from_postgis("SELECT * FROM ubicacion_escuelas WHERE gid <> 3269",conn,geom_col='geom')

points['x'] = points.apply(getPointCoords,geom='geom',coord_type='x',axis=1)
points['y'] = points.apply(getPointCoords,geom='geom',coord_type='y',axis=1)

p_df = points.drop('geom',axis=1).copy()
psource = ColumnDataSource(p_df)

output_file("gmap.html")

map_options = GMapOptions(lat=8.9824, lng=-79.5199, map_type="roadmap",zoom=8)

p = gmap("AIzaSyBmG4umB0ThuiwtDxhNhzx2nJ0lVX4r_44", map_options, title="Centros de Vacunacion",plot_width=900,plot_height=650)

p.circle('x','y', size=3, source=psource, color="black")

my_hover = HoverTool()

my_hover.tooltips = [('Address of the point', '@nombre')]
p.add_tools(my_hover)

#---------------------------------------------------------- QUERY 1 ----------------------------------------------------------

query1 = pd.read_sql_query("SELECT provincia, count(*) as escuelas FROM ubicacion_escuelas WHERE nombre like 'Escuela%' Group by provincia",conn)
df = pd.DataFrame(query1)
provincias = df['provincia']
escuelas =df['escuelas']

# output_file("index.html")

#Add plot
b= figure(y_range=provincias,  plot_width=500, plot_height=500, title="Provincias x Escuelas", x_axis_label="Escuelas",tools="pan,box_select,zoom_in,zoom_out,save,reset")
#Render glyph
b.hbar(y=provincias, right=escuelas,left=0,height=0.4,color="orange",fill_alpha=0.5)

grid = gridplot([[p,b]])

show(grid)

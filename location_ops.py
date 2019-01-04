import geopy
import gpxpy
import unicodedata

try:
    database
    geolocator
except NameError:
    database = {'keys': [], 'values': []}
    geolocator = geopy.Nominatim(user_agent='pic_sort')
    print('Location operations initiated')

def _convert_to_decimal(lat_dir, lat_deg, lat_min, lat_sec, lon_dir, lon_deg, lon_min, lon_sec):
    direction = {'N':1, 'S':-1, 'E': 1, 'W':-1}
    lat_deg = ( lat_deg + lat_min/60. + lat_sec/3600. ) * direction[lat_dir.upper()]
    lon_deg = ( lon_deg + lon_min/60. + lon_sec/3600. ) * direction[lon_dir.upper()]
    return (lat_deg, lon_deg)


def get_location_info(a, b, c=False, d=None, e=None, f=None, g=None, h=None, i=False):
    if d == None:
        lat = a
        lon = b
        normalize = c
    else:
        lat, lon = _convert_to_decimal(a, b, c, d, e, f, g, h)
        normalize = i
    
    raw = geolocator.reverse('{}, {}'.format(lat, lon))

    path_str = '_none_'

    if 'address' in raw.raw:
        if 'country' in raw.raw['address']:
            path_str = raw.raw['address']['country']
        if 'state' in raw.raw['address']:
            path_str += '/' + raw.raw['address']['state']
        elif 'county' in raw.raw['address']:
            path_str += '/' + raw.raw['address']['county']
        if 'state_district' in raw.raw['address']:
            path_str += '/' + raw.raw['address']['state_district']

    path_str = path_str.replace(' ', '_')
    if normalize:
        path_str = unicodedata.normalize('NFKD', path_str).encode('ascii','ignore')

    return {'latitude': lat, 'longitude': lon, 'address': raw.address, 'raw': raw, 'path_str': path_str}

import gpxpy
import unicodedata
import reverse_geocoder


try:
    database
except NameError:
    database = {'times': [], 'points': {}}
    print('Location operations initiated')


def parse_gpx_file(filename):
    with open(filename, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    try:
                        timestamp = point.time.timestamp()
                        if timestamp not in database['times']:
                            latitude = point.latitude
                            longitude = point.longitude
                            database['times'].append(timestamp)
                            database['points'][timestamp] = {'latitude': latitude, 'longitude': longitude}
                    except AttributeError:
                        pass
    database['times'].sort()


def get_gpx_location(timestamp, max_diff):
    if len(database['times']) < 2 or timestamp < database['times'][0] or timestamp > database['times'][-1]:
        return (None, None)
    for i in range(0, len(database['times'])-1):
        t_gpx_1 = database['times'][i]
        t_gpx_2 = database['times'][i+1]
        if timestamp >= t_gpx_1 and timestamp <= t_gpx_2:
            if ( timestamp - t_gpx_1 ) > max_diff or ( t_gpx_2 - timestamp ) > max_diff:
                break
            latitude_1 = database['points'][t_gpx_1]['latitude']; longitude_1 = database['points'][t_gpx_1]['longitude']
            latitude_2 = database['points'][t_gpx_2]['latitude']; longitude_2 = database['points'][t_gpx_2]['longitude']
            fak = ( timestamp - t_gpx_1 ) / ( t_gpx_2 - t_gpx_1 )
            latitude = ( latitude_2 - latitude_1 ) * fak + latitude_1
            longitude = ( longitude_2 - longitude_1 ) * fak + longitude_1
            return (latitude, longitude)
    return (None, None)


def convert_to_decimal(lat_dir, lat_deg, lat_min, lat_sec, lon_dir, lon_deg, lon_min, lon_sec):
    direction = {'N':1, 'S':-1, 'E': 1, 'W':-1}
    lat_deg = ( lat_deg + lat_min/60. + lat_sec/3600. ) * direction[lat_dir.upper()]
    lon_deg = ( lon_deg + lon_min/60. + lon_sec/3600. ) * direction[lon_dir.upper()]
    return (lat_deg, lon_deg)


def get_location_info(latitude, longitude, normalize=False):
    raw = reverse_geocoder.get((latitude,longitude), mode=1)

    path = [ '_none_' ]

    if len(raw['cc']) > 0:
        path = [ raw['cc'] ]
    if len(raw['admin1']) > 0:
        path.append(raw['admin1'])
    if len(raw['admin2']) > 0:
        path.append(raw['admin2'])
    if len(raw['name']) > 0:
        path.append(raw['name'])

    path = [ part.replace(' ', '_') for part in path ]
    if normalize:
        path = [ unicodedata.normalize('NFKD', part).encode('ascii','ignore') for part in path ]

    return {'latitude': latitude, 'longitude': longitude, 'raw': raw, 'path': path}

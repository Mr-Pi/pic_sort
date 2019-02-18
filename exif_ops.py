import exifread
import location_ops


def read_exif_data(source):
    with open(source, 'rb') as f:
        exif_data = exifread.process_file(f)
    return exif_data


def convert_exif_location_decimal(exif_data):
    return location_ops.convert_to_decimal(
            exif_data['GPS GPSLatitudeRef'], exif_data['GPS GPSLatitude'][0], exif_data['GPS GPSLatitude'][1], exif_data['GPS GPSLatitude'][2],
            exif_data['GPS GPSLongitudeRef'], exif_data['GPS GPSLongitude'][0], exif_data['GPS GPSLongitude'][1], exif_data['GPS GPSLongitude'][2])


def serialize_exif_data(exif_data_in, keywords):
    exif_data = {}
    for key in exif_data_in:
        for keyword in keywords:
            if key[0:len(keyword)] == keyword:
                if type(exif_data_in[key]) == exifread.classes.IfdTag:
                    values = exif_data_in[key].values
                    if type(values) == list:
                        new_values = []
                        for value in values:
                            if type(value) == exifread.utils.Ratio:
                                if value.num == 0:
                                    new_values.append(0)
                                else:
                                    new_values.append(value.num/value.den)
                            else:
                                new_values.append(value)
                        values = new_values
                    exif_data[key] = values
                else:
                    exif_data[key] = exif_data_in[key]
    return exif_data

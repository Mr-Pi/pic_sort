# pic_sort

This repo contains a simple python script to find and sort various of pictures.

Each picture/image found is sha512 hashed before it is copied/moved to the destination.
Only one copy of each file is saved, so a file based deduplication is performed.

The pictures are sorted by following aspects:

 * date - extracted from exif data (fallback to modification time when no exif data available)
 * author - extracted from exif data
 * camera model - determined from various exif data
 * location
    * creates following directory tree: `<country code>/<area>/<closer area>/<city>`
	* for each level of the tree a directory named `_all_` is created contains all images/pictures from this area
	* determined by the location from exif data if possible
	* fallback to parsed gpx files and determine approximated location by time matching

For all aspects/categories a directory named `_unknown_` is created contains all remaining files.


## Usage

For a help message simply run `./pic_sort.py -h`.


## License

This work is licensed under a [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).


## Author Information

 * [Markus Mroch (Mr. Pi)](https://github.com/Mr-Pi) _markus.mroch@stuvus.uni-stuttgart.de_

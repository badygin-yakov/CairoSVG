#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of CairoSVG
# Copyright © 2010-2011 Kozea
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CairoSVG.  If not, see <http://www.gnu.org/licenses/>.

"""
Cairo test suite.

This test suite compares the CairoSVG output with the reference output.

"""

import os
import io
import tempfile
import shutil
import subprocess

import png
import cairo

import cairosvg.parser
import cairosvg.surface


REFERENCE_FOLDER = os.path.join(os.path.dirname(__file__), "reference")
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "output")
ALL_FILES = sorted((
        os.path.join(REFERENCE_FOLDER, filename)
        for filename in os.listdir(REFERENCE_FOLDER)
        if os.path.isfile(os.path.join(REFERENCE_FOLDER, filename))),
                   key=lambda name: name.lower())
FILES = zip(ALL_FILES[::2], ALL_FILES[1::2])
PIXEL_TOLERANCE = 65 * 255
SIZE_TOLERANCE = 1


if not os.path.exists(OUTPUT_FOLDER):
    os.mkdir(OUTPUT_FOLDER)


def same(tuple1, tuple2, tolerence=0):
    """Return if the tuples values are quite the same."""
    for value1, value2 in zip(tuple1, tuple2):
        if abs(value1 - value2) > tolerence:
            return False
    return True


def generate_function(description):
    """Return a testing function with the given ``description``."""
    def check_image(png_filename, svg_filename):
        """Check that the pixels match between ``svg`` and ``png``."""
        width1, height1, pixels1, _ = png.Reader(png_filename).asRGBA()
        size1 = (width1, height1)
        png_filename = os.path.join(
            OUTPUT_FOLDER, os.path.basename(png_filename))
        cairosvg.svg2png(url=svg_filename, write_to=png_filename)
        width2, height2, pixels2, _ = png.Reader(png_filename).asRGBA()
        size2 = (width2, height2)

        # Test size
        assert same(size1, size2, SIZE_TOLERANCE), \
            "Bad size (%s != %s)" % (size1, size2)

        # Test pixels
        width = min(width1, width2)
        height = min(height1, height2)
        pixels1 = list(pixels1)
        pixels2 = list(pixels2)
        # x and y are good variable names here
        # pylint: disable=C0103
        for x in range(width):
            for y in range(height):
                pixel_slice = slice(4 * x, 4 * (x + 1))
                pixel1 = list(pixels1[y][pixel_slice])
                alpha_pixel1 = (
                    [pixel1[3] * value for value in pixel1[:3]] +
                    [255 * pixel1[3]])
                pixel2 = list(pixels2[y][pixel_slice])
                alpha_pixel2 = (
                    [pixel2[3] * value for value in pixel2[:3]] +
                    [255 * pixel2[3]])
                assert same(alpha_pixel1, alpha_pixel2, PIXEL_TOLERANCE), \
                    "Bad pixel %i, %i (%s != %s)" % (x, y, pixel1, pixel2)
        # pylint: enable=C0103

    check_image.description = description
    return check_image


def test_images():
    """Yield the functions testing an image."""
    for png_filename, svg_filename in FILES:
        image_name = os.path.splitext(os.path.basename(png_filename))[0]
        yield (
            generate_function("Test the %s image" % image_name),
            png_filename, svg_filename)


MAGIC_NUMBERS = {
    'SVG': '<?xml',
    'PNG': '\211PNG\r\n\032\n',
    'PDF': '%PDF',
    'PS': '%!',
}

SAMPLE_SVG = os.path.join(REFERENCE_FOLDER, 'arcs01.svg')

def test_formats():
    """Convert to a given format and test that output looks right."""
    _png_filename, svg_filename = FILES[0]
    for format in MAGIC_NUMBERS:
        # Use a default parameter value to bind to the current value,
        # not to the variabl as a closure would do.
        def test(format=format):
            content = cairosvg.CONVERTERS[format](url=svg_filename)
            assert content.startswith(MAGIC_NUMBERS[format])
        test.description = 'Test that the output from svg2%s looks like %s' % (
            format.lower(), format)
        yield test


def read_file(filename):
    """Shortcut to return the whole content of a file as a byte string."""
    with open(filename, 'rb') as file_object:
        return file_object.read()


def test_api():
    """Test the Python API with various parameters."""
    _png_filename, svg_filename = FILES[0]
    expected_content = cairosvg.svg2png(url=svg_filename)
    # Already tested above: just a sanity check:
    assert expected_content.startswith(MAGIC_NUMBERS['PNG'])

    svg_content = read_file(svg_filename)
    # Read from a byte string
    assert cairosvg.svg2png(svg_content) == expected_content
    assert cairosvg.svg2png(source=svg_content) == expected_content

    with open(svg_filename, 'rb') as file_object:
        # Read from a real file object
        assert cairosvg.svg2png(file_obj=file_object) == expected_content

    file_like = io.BytesIO(svg_content)
    # Read from a file-like object
    assert cairosvg.svg2png(file_obj=file_like) == expected_content

    file_like = io.BytesIO()
    # Write to a file-like object
    cairosvg.svg2png(svg_content, write_to=file_like)
    assert file_like.getvalue() == expected_content

    temp = tempfile.mkdtemp()
    try:
        temp_1 = os.path.join(temp, 'result_1.png')
        with open(temp_1, 'wb') as file_object:
            # Write to a real file object
            cairosvg.svg2png(svg_content, write_to=file_object)
        assert read_file(temp_1) == expected_content

        temp_2 = os.path.join(temp, 'result_2.png')
        # Write to a filename
        cairosvg.svg2png(svg_content, write_to=temp_2)
        assert read_file(temp_2) == expected_content

    finally:
        shutil.rmtree(temp)


def test_low_level_api():
    """Test the low-level Python API with various parameters."""
    _png_filename, svg_filename = FILES[0]
    expected_content = cairosvg.svg2png(url=svg_filename)

    # Same as above, longer version
    tree = cairosvg.parser.Tree(url=svg_filename)
    file_like = io.BytesIO()
    surface = cairosvg.surface.PNGSurface(tree, file_like)
    surface.finish()
    assert file_like.getvalue() == expected_content

    png_result = png.Reader(bytes=expected_content).read()
    expected_width, expected_height, _, _ = png_result

    # Abstract surface
    surface = cairosvg.surface.PNGSurface(tree, output=None)
    assert surface.width == expected_width
    assert surface.height == expected_height
    assert cairo.SurfacePattern(surface.cairo).get_surface() is surface.cairo

    try:
        cairo.SurfacePattern('Not a cario.Surface object.')
    except TypeError:
        pass
    else:
        assert False, 'expected TypeError'


def test_script():
    script = os.path.join(os.path.dirname(__file__), '..', 'cairosvg.py')
    _png_filename, svg_filename = FILES[0]
    expected_png = cairosvg.svg2png(url=svg_filename)
    expected_pdf = cairosvg.svg2pdf(url=svg_filename)

    def run(*script_args, **kwargs):
        return subprocess.check_output([script] + list(script_args), **kwargs)

    assert run().startswith('Usage: ')
    assert run('--help').startswith('Usage: ')
    assert run('--version').strip() == cairosvg.VERSION
    assert run(svg_filename) == expected_pdf  # default to PDF
    assert run(svg_filename, '-f', 'Pdf') == expected_pdf
    assert run(svg_filename, '-f', 'png') == expected_png
    with open(svg_filename, 'rb') as file_object:
        assert run('-', stdin=file_object) == expected_pdf

    # TODO: test --dpi

    temp = tempfile.mkdtemp()
    try:
        temp_1 = os.path.join(temp, 'result_1')
        run(svg_filename, '-o', temp_1)  # default to PDF
        assert read_file(temp_1) == expected_pdf

        temp_2 = os.path.join(temp, 'result_2.png')
        run(svg_filename, '-o', temp_2)  # Guess from the file extension
        assert read_file(temp_2) == expected_png

        temp_3 = os.path.join(temp, 'result_3.png')
        run(svg_filename, '-o', temp_3, '-f', 'pdf')  # Explicit -f wins
        assert read_file(temp_3) == expected_pdf
    finally:
        shutil.rmtree(temp)

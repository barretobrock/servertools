#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from typing import (
    List
)
from math import (
    ceil,
    sqrt,
    floor
)
from PIL import Image


class GIF:
    """GIF tools"""
    DEG_CONST = 10
    ORIENTATION = -1

    def __init__(self):
        self.Image = Image

    def spin(self, new_name: str, filepath: str, intensity: int = 1, clockwise: bool = False,
             frame_duration_ms: int = 100):
        """Converts image to spinning gif"""
        # Constants
        # Base degrees to rotate
        orientation = self.ORIENTATION if clockwise else 1

        img = self.Image.open(filepath)
        img = self.make_transparent(img, background='black')
        img_list = [img]

        rotate_deg = 0
        while rotate_deg < 400:
            rotate_deg += (self.DEG_CONST * intensity)
            new_img = img.rotate(rotate_deg * orientation)
            new_img = self.make_transparent(new_img, background='black')
            img_list.append(new_img)

        self._save_imgs_to_gif(new_name, img_list, frame_duration_ms)

    def intensifies(self, filepath: str, intensity: int = 1, frame_duration_ms: int = 100):
        """Converts image to shaky gif"""
        # TODO
        pass

    def party(self, filepath: str, frame_duration_ms: int = 100):
        """Converts an image into multiple colored frames"""
        # TODO
        pass

    @staticmethod
    def make_transparent(img: Image, background: str = 'white') -> Image:
        """Makes an image (or frame) transparent by eliminating the white background"""

        img = img.convert("RGBA")
        datas = img.getdata()

        if background == 'white':
            val = 255

        newData = []
        for item in datas:
            if all([x == 255 for x in item[:3]]):
                newData.append((255, 255, 255, 0))
            else:
                if item[0] > 150:
                    newData.append((0, 0, 0, 255))
                else:
                    newData.append(item)

        img.putdata(newData)

        return img

    @staticmethod
    def _save_imgs_to_gif(filename: str, img_list: List[Image.Image], frame_duration_ms: int = 100):
        """Saves images to gif

        Args:
            filename: str, filename to save the gif
            img_list: list of PIL.Image objs
            frame_duration_ms: int, the number of milliseconds per frame
        """
        img_list[0].save(filename, 'gif', save_all=True, append_images=img_list[1:],
                         duration=frame_duration_ms, loop=0)

    def make_gif(self, filename: str, img_list: List[Image.Image], frame_duration_ms: int = 100, ):
        """Makes a gif from a list of images, sorted alphabetically

        Args:
            filename: path to the file
            img_list: list of filepaths
            frame_duration_ms: int, duration of each frame
        """
        images = []
        img_list.sort()
        for fpath in img_list:
            images.append(self.Image.open(fpath))

        self._save_imgs_to_gif(filename, img_list, frame_duration_ms)


class GIFSlice:
    """Slices a gif into squares of determined size"""
    def __init__(self):
        self.Image = Image

    def _validate_image(self, number_tiles):
        """Basic sanity checks prior to performing a split."""
        TILE_LIMIT = 99 * 99

        try:
            number_tiles = int(number_tiles)
        except Exception as _:
            raise ValueError('number_tiles could not be cast to integer.')

        if number_tiles > TILE_LIMIT or number_tiles < 2:
            raise ValueError('Number of tiles must be between 2 and {} (you \
                              asked for {}).'.format(TILE_LIMIT, number_tiles))

    def _calc_columns_rows(self, n):
        """
        Calculate the number of columns and rows required to divide an image
        into ``n`` parts.
        Return a tuple of integers in the format (num_columns, num_rows)
        """
        num_columns = int(ceil(sqrt(n)))
        num_rows = int(ceil(n / float(num_columns)))
        return num_columns, num_rows

    def _get_basename(self, filename):
        """Strip path and extension. Return basename."""
        return os.path.splitext(os.path.basename(filename))[0]

    def _save_tiles(self, tiles, prefix='', directory=os.getcwd(), format='gif', duration_ms=100):
        """
        Write image files to disk. Create specified folder(s) if they
           don't exist. Return list of :class:`Tile` instance.
        Args:
           tiles (list):  List, tuple or set of :class:`Tile` objects to save.
           prefix (str):  Filename prefix of saved tiles.
        Kwargs:
           directory (str):  Directory to save tiles. Created if non-existant.
        Returns:
            Tuple of :class:`Tile` instances.
        """
        for tile in tiles:
            tile.save(filename=tile.generate_filename(prefix=prefix, directory=directory, format=format),
                      format=format, duration_ms=duration_ms)
        return tuple(tiles)

    def _extract_frames(self, gif_path):
        frame = self.Image.open(gif_path)
        n_frames = 0
        frames = []

        while frame:
            frame_rgba = frame.convert(mode='RGBA')
            frames.append(frame_rgba)
            n_frames += 1

            try:
                frame.seek(n_frames)
            except EOFError:
                break
        return frames

    def slice(self, filename, number_tiles, duration_ms=100):
        """
        Split an image into a specified number of tiles.
        Args:
           filename (str):  The filename of the image to split.
           number_tiles (int):  The number of tiles required.
           duration_ms: int, duration of each frame
        Returns:
            Tuple of :class:`GIFTile` instances.
        """
        im = self.Image.open(filename)
        im_w, im_h = im.size

        frames = self._extract_frames(filename)

        columns = 0
        rows = 0

        self._validate_image(number_tiles)
        columns, rows = self._calc_columns_rows(number_tiles)
        extras = (columns * rows) - number_tiles

        tile_w, tile_h = int(floor(im_w / columns)), int(floor(im_h / rows))

        tiles = []
        number = 1
        for pos_y in range(0, im_h - rows, tile_h):  # -rows for rounding error.
            for pos_x in range(0, im_w - columns, tile_w):  # as above.
                area = (pos_x, pos_y, pos_x + tile_w, pos_y + tile_h)
                position = (int(floor(pos_x / tile_w)) + 1,
                            int(floor(pos_y / tile_h)) + 1)
                coords = (pos_x, pos_y)
                # Go through each frame, crop that and save into collection of frames
                cropped_frames = []
                for frame in frames:
                    cropped_frames.append(frame.crop(area))

                giftile = GIFTile(cropped_frames, number, position, coords)
                # Save the cropped frames
                tiles.append(giftile)

        self._save_tiles(tiles, prefix=self._get_basename(filename), directory=os.path.dirname(filename),
                         duration_ms=duration_ms)
        return tuple(tiles)

    def arrange_imgs(self, imgs):
        """Arrange the sliced images in order and prep for display"""
        out_str = ''
        prev_lvl = ''
        stage_emojis = {}
        for i in imgs:
            name = i.basename
            fpath = i.filename
            stage_emojis[name] = fpath
            n_split = name.split('_')
            cur_lvl = n_split[1]
            if cur_lvl != prev_lvl:
                out_str += '\n'
                prev_lvl = n_split[1]

            out_str += ':{}:'.format(name)
        return out_str


class GIFTile(object):
    """Represents a single tile."""

    def __init__(self, image_list, number, position, coords, filename=None):
        self.image_list = image_list
        self.number = number
        self.position = position
        self.coords = coords
        self.filename = filename

    @property
    def row(self):
        return self.position[0]

    @property
    def column(self):
        return self.position[1]

    @property
    def basename(self):
        """Strip path and extension. Return base filename."""
        return self.get_basename(self.filename)

    def generate_filename(self, directory=os.getcwd(), prefix='tile',
                          format='gif', path=True):
        """Construct and return a filename for this tile."""
        filename = prefix + '_{col:02d}_{row:02d}.{ext}'.format(
                      col=self.column, row=self.row, ext=format.lower().replace('jpeg', 'jpg'))
        if not path:
            return filename
        return os.path.join(directory, filename)

    def save(self, filename=None, format='gif', duration_ms=100):
        if not filename:
            filename = self.generate_filename(format=format)
        self.image_list[0].save(filename, format, save_all=True, append_images=self.image_list[1:],
                                duration=duration_ms, loop=0)
        self.filename = filename

    def get_basename(self, filename):
        """Strip path and extension. Return basename."""
        return os.path.splitext(os.path.basename(filename))[0]

    def __repr__(self):
        """Show tile number, and if saved to disk, filename."""
        if self.filename:
            return '<Tile #{} - {}>'.format(self.number,
                                            os.path.basename(self.filename))
        return '<Tile #{}>'.format(self.number)

#!/bin/bash
# Usage: scripts/scene-backgrounds.sh <folder of originals>   (needs ImageMagick 7; the originals are not in the repo)
# The seven background pictures, from the originals to web/public/scene/<sky>.webp:
# day regraded from golden hour to midday; a painted sky; the city and trees flattened to a cartoon's few colours;
# the picture's own terrace replaced by its treetops; mirrored; the bottom edge faded out.
set -e
D=${1:?folder holding the seven original pictures}; S=web/public/scene; T=$(mktemp -d)
for p in "day:Golden Hour Rooftop Cityscape" "night:Moonlit Rooftop Over the City" "cloud:Stormy Rooftop Cityscape" "rain:Rainy Rooftop Overlooking the Stormy City" "storm:Lightning Over a Rain-Soaked City" "sand:Duststorm Over the Hazy City" "snow:Snowy Rooftop Overlooking the City"; do
  sky=${p%%:*}; grade=""
  [ "$sky" = day ] && grade="-channel R -evaluate multiply 0.80 -channel G -evaluate multiply 0.97 -channel B -evaluate multiply 1.22 +channel -modulate 118,80 -sigmoidal-contrast 3x45%"
  magick "$D/${p#*:}.png" -resize 2000x750! -crop 1855x750+0+0 +repage $grade $T/src.png
  magick $T/src.png -kuwahara 3 -dither None -colors 40 -modulate 104,120 $T/toon.png
  magick $T/toon.png \( $T/src.png -kuwahara 5 -kuwahara 3 -modulate 100,112 \) \( -size 1855x300 xc:white -size 1855x50 gradient:white-black -size 1855x400 xc:black -append \) -composite \
    \( -size 1855x750 xc:white -fill black -draw "polygon 0,632 1600,492 1855,492 1855,750 0,750" -blur 0x7 \) -alpha off -compose CopyOpacity -composite $T/top.png
  magick $T/toon.png -crop 700x85+0+500 +repage -resize 1855x300! -kuwahara 3 -modulate 92,105 -background black -gravity south -extent 1855x750 $T/fill.png
  magick $T/fill.png $T/top.png -compose Over -composite -flop \( -size 1855x660 xc:white -size 1855x90 gradient:white-black -append \) -alpha off -compose CopyOpacity -composite -quality 84 $S/$sky.webp
done

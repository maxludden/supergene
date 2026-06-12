#!/usr/bin/env bash

set -euo pipefail

readonly COVER_DIR="assets/covers/super-gene"
readonly REFERENCE_COVER="assets/covers/book01/Book1-cover-decorated.png"
readonly DISPLAY_FONT="/Library/Fonts/NewYorkExtraLarge-Heavy.otf"
readonly SERIF_FONT="${HOME}/Library/Fonts/EBGaramond-VariableFont_wght.ttf"
readonly LABEL_FONT="/System/Library/Fonts/Supplemental/Copperplate.ttc"

make_text_file() {
    local content="$1"
    local file="$2"

    printf '%s' "${content}" > "${file}"
}

draw_title_line() {
    local input_label="$1"
    local text_file="$2"
    local y="$3"
    local size="$4"
    local output_label="$5"

    printf "[%s]" "${input_label}"
    printf "drawtext=fontfile='%s':textfile='%s':fontcolor=0x17110A:fontsize=%s:x=(w-text_w)/2+5:y=%s+6:" "${SERIF_FONT}" "${text_file}" "${size}" "${y}"
    printf "shadowcolor=black@0.35:shadowx=2:shadowy=2,"
    printf "drawtext=fontfile='%s':textfile='%s':fontcolor=0x746D62:fontsize=%s:x=(w-text_w)/2+2:y=%s+2," "${SERIF_FONT}" "${text_file}" "${size}" "${y}"
    printf "drawtext=fontfile='%s':textfile='%s':fontcolor=0xF7F3EA:fontsize=%s:x=(w-text_w)/2:y=%s:" "${SERIF_FONT}" "${text_file}" "${size}" "${y}"
    printf "shadowcolor=black@0.72:shadowx=3:shadowy=3[%s]" "${output_label}"
}

draw_small_caps() {
    local input_label="$1"
    local text_file="$2"
    local y="$3"
    local size="$4"
    local color="$5"
    local output_label="$6"

    printf "[%s]" "${input_label}"
    printf "drawtext=fontfile='%s':textfile='%s':fontcolor=%s:fontsize=%s:x=(w-text_w)/2:y=%s:" "${LABEL_FONT}" "${text_file}" "${color}" "${size}" "${y}"
    printf "shadowcolor=black@0.95:shadowx=2:shadowy=2[%s]" "${output_label}"
}

render_cover() {
    local source="$1"
    local output="$2"
    local _book_label="$3"
    local bottom_label="$4"
    local title_line_1="$5"
    local title_line_2="${6:-}"
    local title_size="${7:-92}"

    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "${tmp_dir}"' RETURN

    local bottom_label_file="${tmp_dir}/bottom-label.txt"
    local title_line_1_file="${tmp_dir}/title-1.txt"
    local title_line_2_file="${tmp_dir}/title-2.txt"
    local subtitle_file="${tmp_dir}/subtitle.txt"
    local producer_file="${tmp_dir}/producer.txt"

    make_text_file "${bottom_label}" "${bottom_label_file}"
    make_text_file "${title_line_1}" "${title_line_1_file}"
    make_text_file "${title_line_2}" "${title_line_2_file}"
    make_text_file "Twelve-Winged Dark Seraphim" "${subtitle_file}"
    make_text_file "PRODUCED BY MAX LUDDEN" "${producer_file}"

    local filter
    filter=$(
        {
            printf "[0:v]format=rgba,"
            printf "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.18:t=fill,"
            printf "drawbox=x=0:y=0:w=iw:h=360:color=black@0.23:t=fill,"
            printf "drawbox=x=0:y=1320:w=iw:h=216:color=black@0.30:t=fill,"
            printf "drawbox=x=18:y=18:w=988:h=1500:color=0xD9C48E@0.72:t=2,"
            printf "drawbox=x=30:y=30:w=964:h=1476:color=0x5F8FD7@0.36:t=1,"
            printf "drawbox=x=47:y=47:w=930:h=1442:color=0xD9C48E@0.42:t=1,"
            printf "drawbox=x=203:y=1390:w=618:h=84:color=0x07152A@0.88:t=fill,"
            printf "drawbox=x=203:y=1390:w=618:h=84:color=0xD6B96E@0.92:t=3,"
            printf "drawbox=x=219:y=1406:w=586:h=52:color=0x6D9DDE@0.35:t=1,"
            printf "drawbox=x=132:y=172:w=760:h=1:color=0xD8C184@0.58:t=fill,"
            printf "drawbox=x=214:y=455:w=596:h=2:color=0xD8C184@0.70:t=fill,"
            printf "drawbox=x=496:y=438:w=28:h=28:color=0xD8C184@0.90:t=2,"
            printf "drawbox=x=503:y=445:w=14:h=14:color=0x6E45C8@0.78:t=fill,"
            printf "drawbox=x=342:y=1324:w=340:h=2:color=0xD8C184@0.70:t=fill[base];"

            printf "[1:v]crop=150:190:0:0,colorkey=0x020509:0.14:0.28,format=rgba,colorchannelmixer=aa=0.92[tl];"
            printf "[1:v]crop=150:190:874:0,colorkey=0x020509:0.14:0.28,format=rgba,colorchannelmixer=aa=0.92[tr];"
            printf "[1:v]crop=170:190:0:1346,colorkey=0x020509:0.14:0.28,format=rgba,colorchannelmixer=aa=0.92[bl];"
            printf "[1:v]crop=170:190:854:1346,colorkey=0x020509:0.14:0.28,format=rgba,colorchannelmixer=aa=0.92[br];"
            printf "[1:v]crop=92:82:466:0,colorkey=0x020509:0.14:0.28,format=rgba,colorchannelmixer=aa=0.88[topgem];"
            printf "[1:v]crop=92:90:466:1446,colorkey=0x020509:0.14:0.28,format=rgba,colorchannelmixer=aa=0.92[bottomgem];"

            printf "[base][tl]overlay=0:0[tmp1];"
            printf "[tmp1][tr]overlay=874:0[tmp2];"
            printf "[tmp2][bl]overlay=0:1346[tmp3];"
            printf "[tmp3][br]overlay=854:1346[tmp4];"
            printf "[tmp4][topgem]overlay=466:0[tmp5];"
            printf "[tmp5][bottomgem]overlay=466:1446[decorated];"

            draw_title_line "decorated" "${title_line_1_file}" 148 "${title_size}" "b"
            if [[ -n "${title_line_2}" ]]; then
                printf ";"
                draw_title_line "b" "${title_line_2_file}" 278 "${title_size}" "c"
                printf ";"
                draw_small_caps "c" "${subtitle_file}" 485 31 "0xD8C184" "d"
            else
                printf ";"
                draw_small_caps "b" "${subtitle_file}" 456 31 "0xD8C184" "d"
            fi
            printf ";"
            draw_small_caps "d" "${producer_file}" 1350 22 "0xD8C184" "e"
            printf ";"
            draw_small_caps "e" "${bottom_label_file}" 1412 38 "0xD8C184" "out"
        }
    )

    ffmpeg -hide_banner -loglevel error -y \
        -i "${COVER_DIR}/${source}" \
        -i "${REFERENCE_COVER}" \
        -filter_complex "${filter}" \
        -map "[out]" \
        -frames:v 1 \
        "${COVER_DIR}/${output}"
}

render_cover \
    "book-02-second-gods-sanctuary.png" \
    "book-02-second-gods-sanctuary-with-text.png" \
    "BOOK TWO" \
    "Book Two of Super Gene" \
    "Second God's" \
    "Sanctuary" \
    "108"

render_cover \
    "book-03-third-gods-sanctuary.png" \
    "book-03-third-gods-sanctuary-with-text.png" \
    "BOOK THREE" \
    "Book Three of Super Gene" \
    "Third God's" \
    "Sanctuary" \
    "108"

render_cover \
    "book-04-fourth-and-fifth-gods-sanctuaries.png" \
    "book-04-fourth-and-fifth-gods-sanctuaries-with-text.png" \
    "BOOK FOUR" \
    "Book Four of Super Gene" \
    "Fourth and Fifth" \
    "God's Sanctuaries" \
    "88"

render_cover \
    "book-05-planet-kate-and-narrow-moon.png" \
    "book-05-planet-kate-and-narrow-moon-with-text.png" \
    "BOOK FIVE" \
    "Book Five of Super Gene" \
    "Planet Kate and" \
    "Narrow Moon" \
    "94"

render_cover \
    "book-06-the-extreme-king.png" \
    "book-06-the-extreme-king-with-text.png" \
    "BOOK SIX" \
    "Book Six of Super Gene" \
    "The Extreme" \
    "King" \
    "108"

render_cover \
    "book-06-ice-blue-knights.png" \
    "book-06-ice-blue-knights-with-text.png" \
    "BOOK SIX" \
    "Book Six of Super Gene" \
    "The Extreme" \
    "King" \
    "108"

render_cover \
    "book-07-the-very-high-and-outer-sky.png" \
    "book-07-the-very-high-and-outer-sky-with-text.png" \
    "BOOK SEVEN" \
    "Book Seven of Super Gene" \
    "The Very High" \
    "and Outer Sky" \
    "92"

render_cover \
    "book-07-fighting-god.png" \
    "book-07-fighting-god-with-text.png" \
    "BOOK SEVEN" \
    "Book Seven of Super Gene" \
    "The Very High" \
    "and Outer Sky" \
    "92"

render_cover \
    "book-08-war-against-the-gods.png" \
    "book-08-war-against-the-gods-with-text.png" \
    "BOOK EIGHT" \
    "Book Eight of Super Gene" \
    "War Against" \
    "the Gods" \
    "108"

render_cover \
    "book-09-god-spirit-blood-pulse.png" \
    "book-09-god-spirit-blood-pulse-with-text.png" \
    "BOOK NINE" \
    "Book Nine of Super Gene" \
    "God Spirit" \
    "Blood-Pulse" \
    "104"

render_cover \
    "book-10-the-thirty-three-skies.png" \
    "book-10-the-thirty-three-skies-with-text.png" \
    "BOOK TEN" \
    "Book Ten of Super Gene" \
    "The Thirty-Three" \
    "Skies" \
    "92"

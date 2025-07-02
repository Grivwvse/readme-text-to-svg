import argparse
import re
import io
import textwrap
import drawsvg as draw
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
import requests


# requements packeges
'''
drawSvg-2.4.0
drawsvg fonttools requests
'''

def text_to_paths(text, font_family, font_size, width, height, l_margin, t_margin, align, text_color, K, output_file, width_auto=False):
    """Преобразует текст в SVG-пути (контуры) с поддержкой автоматической ширины"""
    # Загружаем шрифт
    font_url = f"https://fonts.googleapis.com/css2?family={font_family.replace(' ', '+')}"
    r = requests.get(font_url, headers={"User-Agent": "Mozilla/5.0"})
    
    # Извлекаем URL шрифта
    font_file_url = None
    for line in r.text.split('\n'):
        if '.ttf' in line and 'url(' in line:
            match = re.search(r'url\((.*?)\)', line)
            if match:
                font_file_url = match.group(1)
                break
    
    if not font_file_url:
        raise Exception(f"Не удалось найти URL шрифта для {font_family}")
    
    # Загружаем файл шрифта
    font_data = requests.get(font_file_url).content
    font = TTFont(io.BytesIO(font_data))
    
    # Получаем таблицу сопоставления Unicode символов и глифов
    cmap = font['cmap'].getBestCmap()
    
    # Получаем набор глифов
    glyph_set = font.getGlyphSet()
    
    # Масштаб для преобразования единиц шрифта в пиксели
    scale = font_size / font['head'].unitsPerEm

    # Разбиваем текст на строки с учетом автоширины
    if width_auto:
        # При автоширине не переносим строки автоматически, только по переносам в тексте
        lines = text.split('\n')
    else:
        chars_per_line = int(width / (font_size * K))
        lines = textwrap.wrap(text, width=chars_per_line)
    
    # Рассчитываем реальную ширину, если width_auto=True
    if width_auto:
        # Определяем максимальную ширину строки
        max_line_width = 0
        for line in lines:
            line_width = sum([glyph_set[cmap.get(ord(c), '.notdef')].width for c in line if ord(c) in cmap]) * scale
            max_line_width = max(max_line_width, line_width)
        
        # Добавляем отступы слева и справа (20% от максимальной ширины строки)
        width = max_line_width + (font_size * 4)  # Добавляем отступ
    
    # Создаем SVG с итоговой шириной
    d = draw.Drawing(width, height)
    
    # Определяем базовую позицию текста
    center_x = width * (l_margin / 100)
    
    # Расчет отступа сверху
    min_y_padding = font_size 
    if t_margin == 0:
        center_y = min_y_padding
    else:
        center_y = max(min_y_padding, height * (t_margin / 100))
    
    # Для многострочного текста
    if len(lines) > 1:
        vertical_space_needed = (len(lines) - 1) * font_size / 2
        center_y = max(center_y, min_y_padding + vertical_space_needed)
    
    # Вертикальное смещение для центрирования многострочного текста
    y_offset = -(len(lines) - 1) * font_size / 2
    
    # Обрабатываем каждую строку
    for i, line in enumerate(lines):
        # Определяем позицию Y для текущей строки
        line_y = center_y + (y_offset if i == 0 else font_size * i)
        
        # Определяем начальную позицию X в зависимости от выравнивания
        line_width = sum([glyph_set[cmap.get(ord(c), '.notdef')].width for c in line if ord(c) in cmap]) * scale
        
        if align == "middle":
            line_x = center_x - (line_width / 2)
        elif align == "end":
            line_x = center_x - line_width
        else:  # "start"
            line_x = center_x
        
        # Обрабатываем каждый символ в строке
        x_pos = line_x
        for char in line:
            if ord(char) in cmap:
                glyph_name = cmap[ord(char)]
                
                # Получаем контур глифа
                pen = SVGPathPen(glyph_set)
                glyph_set[glyph_name].draw(pen)
                path_data = pen.getCommands()
                
                if path_data:
                    # Преобразуем HEX цвет в RGB компоненты
                    if text_color.startswith('#'):
                        # Используем hex-строку напрямую вместо преобразования в RGB-кортеж
                        fill_color = text_color
                    else:
                        # Для именованных цветов также используем строку
                        fill_color = text_color
                    
                    # Создаем path-элемент и добавляем в SVG
                    path = draw.Path(fill=fill_color)
                    path.args['d'] = path_data
                    
                    # Применяем трансформацию (масштаб и позиционирование)
                    path.args['transform'] = f'translate({x_pos},{line_y}) scale({scale},{-scale})'
                    
                    d.append(path)
                
                # Увеличиваем x-координату для следующего символа
                x_pos += glyph_set[glyph_name].width * scale
            
            # Пробел или неизвестный символ
            elif char == ' ':
                x_pos += glyph_set['space'].width * scale if 'space' in glyph_set else font_size * 0.3
    
    # Сохраняем SVG
    d.save_svg(output_file)
    print(f"SVG с контурами создан: {output_file}")
    return True




if __name__ == '__main__':
    # Cheacking parameters
    parser = argparse.ArgumentParser(description='Convert Text to SVG Using Google Fonts')

    # Checking if the text is provided or a file path
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--text', type=str, help='Text to convert to SVG.')
    group.add_argument('--file', type=str, help='File path containing text to convert to SVG.')

    # Adding other parameters
    parser.add_argument('--font_size', type=int, default=14, help='font size (Example: 40).')
    parser.add_argument('--font_family', type=str, default='Roboto', help='Name of the Google Font (Example: Roboto).')
    parser.add_argument('--width', type=str, default='auto', help='Width of SVG (Example: 500 or "auto" for automatic width based on text).')
    parser.add_argument('--height', type=int, default='200', help='Height of SVG (Example: 200).')
    parser.add_argument('--align', type=str, default='middle', help='Alignment of text (Example: middle). start, middle, end.')
    parser.add_argument('--l_margin', type=int, default='0', help='Margin from the left side of the SVG (Example: 0).')
    parser.add_argument('--t_margin', type=int, default='0', help='Margin from the top side of the SVG (Example: 0).')
    parser.add_argument('--output', type=str, default='output.svg', help='Name of the output SVG file (Example: output.svg).')
    parser.add_argument('--color', type=str, default='black', help='Text color (Example: red, #FF5500.')
    parser.add_argument('--k', type=float, default=0.6, help='Coefficient for calculating characters per line based on font size and width (Example: 0.6).')
    
    args = parser.parse_args()

    # Getting the text from command line argument or file
    text = args.text
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error occurred while reading the file: {e}")
            exit(1)

    # Определяем ширину
    if args.width.lower() == 'auto':
        width_auto = True
        width = 2000  
    else:
        width_auto = False
        width = int(args.width)

    try:
        output_paths = args.output.replace('.svg', '_paths.svg')
        text_to_paths(text, args.font_family, args.font_size, width, args.height, 
                      args.l_margin, args.t_margin, args.align, args.color, args.k, output_paths, width_auto)
    except Exception as e:
        print(f"Ошибка при создании SVG с контурами: {e}")

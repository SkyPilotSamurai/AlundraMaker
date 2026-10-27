"""Editor dialogue layout using source-reported randomizer text metrics.

Metrics/control convention: Dinopony/alundra-randomizer
4bbc2bdf7a82adeb1d9ff5a3ab8b11033efe9b5c, src/tools/textbox_formatter.cpp.
These are source-reported widths, not independently measured font pixels.
Independent Python implementation; metric provenance retained under MIT:
Copyright (c) 2022 Dinopony. See dialogue_layout-LICENSE.txt.
"""
import re

WIDTHS=dict(zip('wmnHhaApIitl !.,',[24,24,18,18,16,16,16,16,10,10,10,10,10,8,6,6]))
LINE_WIDTH=500
PAGE_LINES=3

def tokens(text):
    text=text.replace('\r\n','\n').replace('\r','\n')
    word='';position=0
    while position<len(text):
        char=text[position]
        if char not in (' ','\t','\n','\\'):
            word+=char;position+=1;continue
        if word:yield word;word=''
        if char=='\n':yield '\\N';position+=1;continue
        if char in (' ','\t'):position+=1;continue
        if position+1>=len(text):raise ValueError('Dialogue ends with an incomplete control')
        end=position+2;kind=text[position+1]
        if kind=='W':
            if end>=len(text) or text[end] not in '0123456789':raise ValueError('Dialogue wait needs one digit')
            end+=1
        elif kind=='0':
            close=text.find('\\Y',end)
            if close<0:raise ValueError('Dialogue choice needs closing \\Y')
            end=close+2
        yield text[position:end];position=end
    if word:yield word

def format_dialogue(text):
    if not isinstance(text,str):raise ValueError('Dialogue needs text')
    try:text.encode('latin-1')
    except UnicodeEncodeError:raise ValueError("Dialogue contains characters outside the game's byte character set")
    if '\0' in text:raise ValueError('Dialogue cannot contain a zero byte')
    output=[];width=0;line=0;space=False
    def newline(force_page=False):
        nonlocal width,line,space
        if force_page or line>=PAGE_LINES-1:output.append('\\A');line=0
        else:output.append('\\N');line+=1
        width=0;space=False
    for token in tokens(text):
        if token.startswith('\\'):
            if token=='\\N':newline()
            elif token=='\\A':newline(True)
            else:output.append(token);space=False
            continue
        size=sum(WIDTHS.get(c,14) for c in token)
        if width+size+(10 if space else 0)<=LINE_WIDTH:
            if space:output.append(' ');width+=10
            output.append(token);width+=size
        elif size<=LINE_WIDTH:
            newline();output.append(token);width+=size
        else:
            if width:newline()
            for char in token:
                amount=WIDTHS.get(char,14)
                if width+amount>LINE_WIDTH:newline()
                output.append(char);width+=amount
        space=True
    return ''.join(output)

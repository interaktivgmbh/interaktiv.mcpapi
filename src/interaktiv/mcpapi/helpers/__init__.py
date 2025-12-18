from html.parser import HTMLParser


class SlateHTMLParser(HTMLParser):
    TAG_MAP = {
        'p': 'p',
        'h1': 'h1',
        'h2': 'h2',
        'h3': 'h3',
        'h4': 'h4',
        'h5': 'h5',
        'h6': 'h6',
        'ul': 'ul',
        'ol': 'ol',
        'li': 'li',
        'blockquote': 'blockquote',
        'a': 'link',
        'strong': 'strong',
        'b': 'strong',
        'em': 'em',
        'i': 'em',
        'u': 'u',
        's': 's',
        'code': 'code',
    }

    BLOCK_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote'}
    INLINE_TAGS = {'strong', 'b', 'em', 'i', 'u', 's', 'code'}

    def __init__(self):
        super().__init__()
        self.result = []
        self.stack = [self.result]
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)


        print('####')
        print('####')
        print(attrs_dict)

        if tag in self.BLOCK_TAGS or tag in self.INLINE_TAGS:
            slate_type = self.TAG_MAP.get(tag, 'p')
            node = {'type': slate_type, 'children': []}
            self.stack[-1].append(node)
            self.stack.append(node['children'])

        elif tag == 'a':
            url = attrs_dict.get('href', '')
            node = {
                'type': 'link',
                'data': {'url': url},
                'children': []
            }
            self.stack[-1].append(node)
            self.stack.append(node['children'])

    def handle_endtag(self, tag):
        if tag in self.BLOCK_TAGS or tag in self.INLINE_TAGS or tag == 'a':
            if len(self.stack) > 1:
                self.stack.pop()

    def handle_data(self, data):
        text = data
        if not text:
            return

        self.text_parts.append(text)

        text_node = {'text': text}
        self.stack[-1].append(text_node)

    def get_result(self):
        plaintext = ''.join(self.text_parts)
        return self.result, plaintext

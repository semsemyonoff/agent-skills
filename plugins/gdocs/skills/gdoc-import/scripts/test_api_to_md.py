import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(text, style=None):
    return {'textRun': {'content': text, 'textStyle': style or {}}}


def para(*elements, style='NORMAL_TEXT', bullet=None):
    p = {'elements': list(elements), 'paragraphStyle': {'namedStyleType': style}}
    if bullet:
        p['bullet'] = bullet
    return {'paragraph': p}


def cell(text):
    return {'content': [para(run(text + '\n'))]}


MONO = {'weightedFontFamily': {'fontFamily': 'Roboto Mono'}}
DOC = {'content': {'title': 'T', 'tabs': [{'tabProperties': {'title': 'Tab 1'}, 'documentTab': {
    'lists': {'L': {'listProperties': {'nestingLevels': [{'glyphType': 'DECIMAL'}, {'glyphSymbol': '●'}]}}},
    'body': {'content': [
        {'sectionBreak': {}},
        para(run('Contents\n'), style='SUBTITLE'),
        {'tableOfContents': {}},
        para(run('1. Intro\n'), style='HEADING_1'),
        para(run('See '), run('docs', {'link': {'url': 'https://x'}, 'bold': True}),
             run(' and '), run('a_b*c', {'italic': True}), run(' end. \n')),
        para(run('first\n'), bullet={'listId': 'L'}),
        para(run('nested\n'), bullet={'listId': 'L', 'nestingLevel': 1}),
        para(run('{\n', MONO)), para(run('\n')), para(run('  "a": "x\\\\y"\n', MONO)), para(run('}\n', MONO)),
        para({'textRun': {'content': 'dropped', 'suggestedInsertionIds': ['s']}}, run('kept\n')),
        {'table': {'tableRows': [
            {'tableCells': [cell('**H1**'), cell('a|b')]},
            {'tableCells': [cell('1'), {'content': [para(run('l1\n')), para(run('l2\n'))]}]},
        ]}},
    ]}}}]}}


class ApiToMdTest(unittest.TestCase):
    def convert(self, cmd, *payloads):
        with tempfile.TemporaryDirectory() as d:
            srcs = []
            for i, payload in enumerate(payloads):
                src = Path(d, f'in{i}.json')
                src.write_text(json.dumps(payload))
                srcs.append(str(src))
            dst = Path(d, 'out.md')
            subprocess.run([sys.executable, '-I', str(HERE / 'api_to_md.py'), cmd, *srcs, str(dst)],
                           check=True, capture_output=True)
            return dst.read_text()

    def test_doc(self):
        md = self.convert('doc', DOC)
        self.assertNotIn('Contents', md)
        self.assertIn('<!-- TOC -->\n\n# 1. Intro', md)
        self.assertIn('See [**docs**](https://x) and *a_b*c* end.\n', md)
        self.assertIn('1. first\n   - nested', md)
        self.assertIn('```json\n{\n  "a": "x\\\\y"\n}\n```', md)
        self.assertIn('\n\nkept\n', md)
        self.assertNotIn('dropped', md)
        self.assertIn('| H1 | a\\|b |\n| --- | --- |\n| 1 | l1<br>l2 |', md)

    def test_sheets(self):
        md = self.convert('sheet',
                          {'range': "'My ''s'!A1:C4", 'values': [['a', 'b', ''], ['1'], [], ['', '']]},
                          {'content': {'range': 'S2!A1:A1', 'values': []}})
        self.assertEqual(md, "## My 's\n\n| a | b |\n| --- | --- |\n| 1 |  |\n\n## S2\n\n(empty)\n")

    def test_grid_data(self):
        chip = {'chip': {'richLinkProperties': {'uri': 'https://docs/d/1'}}}
        md = self.convert('sheet', {'sheets': [
            {'properties': {'title': 'Main'}, 'data': [{'rowData': [
                {'values': [{'formattedValue': 'Doc'}, {}, {'formattedValue': 'Note'}]},
                {'values': [{'formattedValue': 'A | B (part 5)', 'chipRuns': [chip, {'startIndex': 5}]},
                            {},
                            {'formattedValue': 'see divan.ru now', 'textFormatRuns': [
                                {'format': {}}, {'startIndex': 4, 'format': {'link': {'uri': 'http://divan.ru/'}}},
                                {'startIndex': 12, 'format': {}}]}]},
                {'values': [{'formattedValue': 'https://x/y', 'hyperlink': 'https://x/y'},
                            {}, {'formattedValue': 'go', 'hyperlink': 'https://z'}]},
            ]}]},
            {'properties': {'title': 'Info'}, 'data': [{'rowData': [
                {'values': [{'formattedValue': 'Title'}]}, {}, {'values': [{'formattedValue': 'Line'}]}]}]},
        ]})
        self.assertEqual(md, '## Main\n\n| Doc | Note |\n| --- | --- |\n'
                             '| [A \\| B](https://docs/d/1) (part 5) | see divan.ru now |\n'
                             '| https://x/y | [go](https://z) |\n\n'
                             '## Info\n\nTitle\n\nLine\n')


if __name__ == '__main__':
    unittest.main()

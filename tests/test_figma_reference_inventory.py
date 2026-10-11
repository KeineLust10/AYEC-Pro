"""Reference extraction must retain controls and never imply visual matching."""

import pytest

from tools.quality.figma_reference_inventory import DEFAULT_REFERENCES, ReferenceHTML, inventory


def test_nested_control_text_inputs_and_external_dependencies_are_retained():
    parser = ReferenceHTML()
    parser.feed('<script src="https://example.test/library.js">ignore()</script>'
                '<h1>Settings</h1><button title="Save"><span>Apply</span> changes</button>'
                '<table><tr><th>Name</th><td>A &amp; B</td></tr></table>'
                '<input name="customer" placeholder="Search" value="Ada">'
                '<select name="status"><option value="active">Active</option></select>')
    contract = parser.contract()
    assert [(entry['tag'], entry['text']) for entry in contract['elements']] == [
        ('h1', 'Settings'), ('button', 'Apply changes'), ('th', 'Name'), ('td', 'A & B'),
        ('option', 'Active')]
    assert contract['inputs'][0]['attributes']['name'] == 'customer'
    assert contract['inputs'][1]['attributes']['name'] == 'status'
    assert contract['dependencies'][0]['uri'] == 'https://example.test/library.js'
    assert contract['design_code_blocks'][0]['text'] == 'ignore()'


@pytest.mark.skipif(not DEFAULT_REFERENCES.is_dir(), reason="External user reference folder is unavailable")
def test_actual_all_seven_parts_are_ordered_and_not_claimed_complete():
    report = inventory(DEFAULT_REFERENCES)
    assert [part['part'] for part in report['parts']] == list(range(1, 8))
    assert all(part['screens'] for part in report['parts'])
    assert report['status'] == 'inventory_only'
    assert report['screens'] > 30
    for part in report['parts']:
        for screen in part['screens']:
            assert screen['matching_status'] == 'unverified'
            for artifact in screen['artifacts']:
                assert len(artifact['sha256']) == 64

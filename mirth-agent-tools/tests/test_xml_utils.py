from pathlib import Path

from mirth_agent_tools.xml_utils import diff_xml, parse_channel_list, parse_channel_summary


def test_parse_channel_summary() -> None:
    xml = (Path(__file__).parent / "fixtures" / "sample_channel.xml").read_text(encoding="utf-8")
    summary = parse_channel_summary(xml)
    assert summary.id == "sample-channel-id"
    assert summary.name == "Sample Channel"


def test_parse_channel_list() -> None:
    xml = """
    <list>
      <channel><id>one</id><name>One</name></channel>
      <channel><id>two</id><name>Two</name></channel>
    </list>
    """
    summaries = parse_channel_list(xml)
    assert [item.id for item in summaries] == ["one", "two"]


def test_diff_xml() -> None:
    diff = diff_xml("<name>Old</name>", "<name>New</name>")
    assert "--- before.xml" in diff
    assert "+++ after.xml" in diff
    assert "-<name>Old</name>" in diff
    assert "+<name>New</name>" in diff

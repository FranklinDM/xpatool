import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    XML_DECL = auto()
    PROCESSING_INSTRUCTION = auto()
    DOCTYPE = auto()
    COMMENT = auto()
    CDATA = auto()
    START_TAG = auto()
    SELF_CLOSING_TAG = auto()
    END_TAG = auto()
    TEXT = auto()


@dataclass
class Token:
    type: TokenType
    raw: str
    tag_name: str = ""
    attrs: Sequence[tuple[str, str]] | None = None


# Robust attribute parser regex
ATTR_REGEX = re.compile(r'([a-zA-Z0-9_:-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')


def parse_attributes(attr_str: str) -> list[tuple[str, str]]:
    """Extract attribute key-value pairs without modifying or expanding entity values."""
    attrs: list[tuple[str, str]] = []
    for match in ATTR_REGEX.finditer(attr_str):
        name = match.group(1)
        val_double = match.group(2)
        val_single = match.group(3)
        val = (
            val_double
            if val_double is not None
            else (val_single if val_single is not None else "")
        )
        attrs.append((name, val))
    return attrs


def extract_tag_details(
    tag_raw: str, is_self_closing: bool
) -> tuple[str, list[tuple[str, str]]]:
    """Parse tag name and attributes from start or self-closing tag."""
    inner = tag_raw[1:-2].strip() if is_self_closing else tag_raw[1:-1].strip()
    parts = inner.split(None, 1)
    tag_name = parts[0]
    attrs_str = parts[1] if len(parts) > 1 else ""
    return tag_name, parse_attributes(attrs_str)


class XULFormatter:
    def __init__(
        self,
        indent_size: int = 4,
        indent_char: str = " ",
        max_attrs_per_line: int = 1,
        max_line_length: int = 100,
        sort_attributes: bool = False,
        space_before_self_closing: bool = True,
        align_attributes: bool = False,
    ) -> None:
        self.indent = indent_char * indent_size
        self.indent_size = indent_size
        self.indent_char = indent_char
        self.max_attrs_per_line = max_attrs_per_line
        self.max_line_length = max_line_length
        self.sort_attributes = sort_attributes
        self.space_before_self_closing = space_before_self_closing
        self.align_attributes = align_attributes

    def tokenize(self, content: str) -> list[Token]:
        tokens: list[Token] = []
        pos = 0
        length = len(content)

        while pos < length:
            if content.startswith("<!--", pos):
                end_idx = content.find("-->", pos)
                if end_idx == -1:
                    tokens.append(Token(TokenType.COMMENT, content[pos:].strip()))
                    break
                tokens.append(
                    Token(TokenType.COMMENT, content[pos : end_idx + 3].strip())
                )
                pos = end_idx + 3
            elif content.startswith("<![CDATA[", pos):
                end_idx = content.find("]]>", pos)
                if end_idx == -1:
                    tokens.append(Token(TokenType.CDATA, content[pos:].strip()))
                    break
                tokens.append(
                    Token(TokenType.CDATA, content[pos : end_idx + 3].strip())
                )
                pos = end_idx + 3
            elif content.startswith("<!DOCTYPE", pos):
                # Search matching DOCTYPE closing > taking into account internal [ ... ]
                bracket_open = content.find("[", pos)
                gt_direct = content.find(">", pos)
                if bracket_open != -1 and bracket_open < gt_direct:
                    bracket_close = content.find("]", bracket_open)
                    if bracket_close != -1:
                        end_gt = content.find(">", bracket_close)
                        if end_gt != -1:
                            tokens.append(
                                Token(
                                    TokenType.DOCTYPE, content[pos : end_gt + 1].strip()
                                )
                            )
                            pos = end_gt + 1
                            continue
                if gt_direct != -1:
                    tokens.append(
                        Token(TokenType.DOCTYPE, content[pos : gt_direct + 1].strip())
                    )
                    pos = gt_direct + 1
                else:
                    tokens.append(Token(TokenType.DOCTYPE, content[pos:].strip()))
                    break
            elif content.startswith("<?xml", pos):
                end_idx = content.find("?>", pos)
                if end_idx == -1:
                    tokens.append(Token(TokenType.XML_DECL, content[pos:].strip()))
                    break
                tokens.append(
                    Token(TokenType.XML_DECL, content[pos : end_idx + 2].strip())
                )
                pos = end_idx + 2
            elif content.startswith("<?", pos):
                end_idx = content.find("?>", pos)
                if end_idx == -1:
                    tokens.append(
                        Token(TokenType.PROCESSING_INSTRUCTION, content[pos:].strip())
                    )
                    break
                tokens.append(
                    Token(
                        TokenType.PROCESSING_INSTRUCTION,
                        content[pos : end_idx + 2].strip(),
                    )
                )
                pos = end_idx + 2
            elif content.startswith("</", pos):
                end_idx = content.find(">", pos)
                if end_idx == -1:
                    break
                raw_tag = content[pos : end_idx + 1].strip()
                tag_name = raw_tag[2:-1].strip()
                tokens.append(Token(TokenType.END_TAG, raw_tag, tag_name=tag_name))
                pos = end_idx + 1
            elif content.startswith("<", pos):
                # Find tag end respecting quotes
                end_idx = -1
                in_quote: str | None = None
                curr = pos + 1
                while curr < length:
                    ch = content[curr]
                    if in_quote:
                        if ch == in_quote:
                            in_quote = None
                    elif ch in ('"', "'"):
                        in_quote = ch
                    elif ch == ">":
                        end_idx = curr
                        break
                    curr += 1

                if end_idx == -1:
                    break

                raw_tag = content[pos : end_idx + 1].strip()
                is_self = raw_tag.endswith("/>")
                tag_name, attrs = extract_tag_details(raw_tag, is_self_closing=is_self)
                token_type = (
                    TokenType.SELF_CLOSING_TAG if is_self else TokenType.START_TAG
                )
                tokens.append(
                    Token(token_type, raw_tag, tag_name=tag_name, attrs=attrs)
                )
                pos = end_idx + 1
            else:
                next_tag = content.find("<", pos)
                if next_tag == -1:
                    text = content[pos:].strip()
                    if text:
                        tokens.append(Token(TokenType.TEXT, text))
                    break
                text = content[pos:next_tag].strip()
                if text:
                    tokens.append(Token(TokenType.TEXT, text))
                pos = next_tag

        return tokens

    def _format_attributes(
        self,
        tag_name: str,
        attrs: Sequence[tuple[str, str]],
        base_indent: str,
        is_self_closing: bool,
    ) -> str:
        close_marker = " />" if self.space_before_self_closing else "/>"
        closing = close_marker if is_self_closing else ">"
        if not attrs:
            return f"{base_indent}<{tag_name}{closing}"

        formatted_attrs = (
            sorted(attrs, key=lambda item: item[0])
            if self.sort_attributes
            else list(attrs)
        )

        single_line_attrs = " ".join(f'{k}="{v}"' for k, v in formatted_attrs)
        single_line = f"{base_indent}<{tag_name} {single_line_attrs}{closing}"
        if (
            len(formatted_attrs) <= self.max_attrs_per_line
            and len(single_line) <= self.max_line_length
        ):
            return single_line

        if self.align_attributes:
            # first attr on opening line, following attrs aligned to tag column
            align_spaces = " " * (len(base_indent) + len(tag_name) + 2)
            first_k, first_v = formatted_attrs[0]
            lines = [f'{base_indent}<{tag_name} {first_k}="{first_v}"']
            for k, v in formatted_attrs[1:]:
                lines.append(f'{align_spaces}{k}="{v}"')
            lines[-1] = f"{lines[-1]}{closing}"
            return "\n".join(lines)

        attr_indent = base_indent + self.indent
        lines = [f"{base_indent}<{tag_name}"]
        for k, v in formatted_attrs:
            lines.append(f'{attr_indent}{k}="{v}"')
        lines[-1] = f"{lines[-1]}{closing}"
        return "\n".join(lines)

    def _format_doctype(self, doctype_raw: str, base_indent: str) -> str:
        lines = doctype_raw.splitlines()
        if len(lines) == 1:
            return f"{base_indent}{doctype_raw.strip()}"

        formatted_lines: list[str] = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if i == 0 or stripped in ("]>", ">"):
                formatted_lines.append(f"{base_indent}{stripped}")
            else:
                formatted_lines.append(f"{base_indent}{self.indent}{stripped}")
        return "\n".join(formatted_lines)

    def format(self, content: str) -> str:
        tokens = self.tokenize(content)
        output_lines: list[str] = []
        indent_level = 0
        prev_token_type: TokenType | None = None
        i = 0
        num_tokens = len(tokens)

        while i < num_tokens:
            token = tokens[i]
            curr_indent = self.indent * indent_level

            # Check for inline text element pattern: START_TAG -> TEXT -> END_TAG
            if (
                token.type == TokenType.START_TAG
                and i + 2 < num_tokens
                and tokens[i + 1].type == TokenType.TEXT
                and tokens[i + 2].type == TokenType.END_TAG
                and tokens[i + 2].tag_name == token.tag_name
                and "\n" not in tokens[i + 1].raw
            ):
                text_content = tokens[i + 1].raw.strip()
                open_tag = self._format_attributes(
                    token.tag_name,
                    token.attrs or [],
                    curr_indent,
                    is_self_closing=False,
                )
                # Check if opening tag is single line
                if "\n" not in open_tag:
                    inline_line = f"{open_tag}{text_content}</{token.tag_name}>"
                    if len(inline_line) <= self.max_line_length:
                        output_lines.append(inline_line)
                        prev_token_type = TokenType.END_TAG
                        i += 3
                        continue

            # Blank line separation between header blocks
            if (
                token.type
                in (
                    TokenType.DOCTYPE,
                    TokenType.START_TAG,
                )
                and prev_token_type
                in (
                    TokenType.XML_DECL,
                    TokenType.PROCESSING_INSTRUCTION,
                    TokenType.DOCTYPE,
                )
                and output_lines
                and output_lines[-1] != ""
            ):
                output_lines.append("")

            if token.type == TokenType.XML_DECL:
                output_lines.append(token.raw)
            elif token.type == TokenType.PROCESSING_INSTRUCTION:
                output_lines.append(f"{curr_indent}{token.raw}")
            elif token.type == TokenType.DOCTYPE:
                output_lines.append(self._format_doctype(token.raw, curr_indent))
            elif token.type == TokenType.COMMENT or token.type == TokenType.CDATA:
                output_lines.append(f"{curr_indent}{token.raw}")
            elif token.type == TokenType.START_TAG:
                formatted_tag = self._format_attributes(
                    token.tag_name,
                    token.attrs or [],
                    curr_indent,
                    is_self_closing=False,
                )
                output_lines.append(formatted_tag)
                indent_level += 1
            elif token.type == TokenType.SELF_CLOSING_TAG:
                formatted_tag = self._format_attributes(
                    token.tag_name,
                    token.attrs or [],
                    curr_indent,
                    is_self_closing=True,
                )
                output_lines.append(formatted_tag)
            elif token.type == TokenType.END_TAG:
                indent_level = max(0, indent_level - 1)
                curr_indent = self.indent * indent_level
                output_lines.append(f"{curr_indent}</{token.tag_name}>")
            elif token.type == TokenType.TEXT:
                output_lines.append(f"{curr_indent}{token.raw}")

            prev_token_type = token.type
            i += 1

        return "\n".join(output_lines) + "\n"

#!/usr/bin/env node
// make_msg.mjs: write Outlook .msg files (MS-OXMSG inside MS-CFB) from JSON specs.
// Dev tool for the demo corpus. Its outputs are committed; node_modules is not.
//
// Build (from the repository root):
//   cd demo/build/msg && npm ci && node make_msg.mjs specs/*.json
// Verify (oxmsg, msgconvert, olefile): python3 demo/build/msg/verify_msg.py
//
// Usage:
//   node make_msg.mjs [SPEC.json...]           write each spec to its "out" path
//   node make_msg.mjs SPEC.json --out FILE     write one spec to FILE instead
//   node make_msg.mjs --check [SPEC.json...]   rebuild in memory; exit 1 if a written file differs
//   Without SPEC arguments: every specs/*.json next to this script (no shell glob needed).
// Exit codes: 0 ok; 1 check failed; 2 usage or spec error.
//
// Spec fields (JSON). Paths are relative to the repository root.
//   out          output .msg path
//   from         {name, address}
//   to, cc       [{name, address}, ...]; cc may be empty or absent
//   subject      string
//   date         RFC 2822 with offset, e.g. "Wed, 28 Oct 2026 09:10:00 +0100"; weekday is checked
//   message_id   "<id@domain>" (angle brackets optional)
//   in_reply_to  "<id@domain>" or ""
//   references   "<a@x> <b@y>", a list of ids, or ""
//   body         string, or a list of lines joined with "\n"; stored with CRLF line ends
//   attachments  [{path, name, mime}, ...]; name defaults to the file name of path
//
// What is written (MS-OXMSG):
//   root storage, CLSID {00020D0B-0000-0000-C000-000000000046}:
//     __properties_version1.0: 32-byte header (8 reserved, next recipient id, next attachment
//       id, recipient count, attachment count, 8 reserved), then one 16-byte entry per property
//       (tag, flags 0x6, value). PT_LONG, PT_BOOLEAN and PT_SYSTIME (FILETIME) values sit in the
//       entry. PT_UNICODE and PT_BINARY entries hold the byte size and a zero reserved field;
//       for PT_UNICODE the size counts the 2-byte terminator, which the stream does not hold.
//     __substg1.0_XXXXYYYY: one stream per PT_UNICODE (001F, UTF-16LE) or PT_BINARY (0102) value.
//     __nameid_version1.0: __substg1.0_00020102, _00030102, _00040102, empty (no named properties).
//     __recip_version1.0_#0000000N: 8-byte header; type (1 To, 2 Cc), name, SMTP address.
//     __attach_version1.0_#0000000N: 8-byte header; attached by value (method 1), data, names.
//   Message properties: class IPM.Note; subject, normalized subject and conversation topic
//     (an Outlook prefix such as "RE: " goes to PR_SUBJECT_PREFIX); body; sender and
//     sent-representing name, address, SMTP and type SMTP; display To, Cc, Bcc; Message-ID;
//     In-Reply-To and References only when set; flags (read, has attachment); has-attach;
//     importance normal; Internet code page 65001; store support mask with STORE_UNICODE_OK.
//   PR_TRANSPORT_MESSAGE_HEADERS holds an RFC 5322 header block, CRLF line ends: From, To, Cc
//     (when any), Subject, Date, Message-ID, In-Reply-To and References (when set),
//     MIME-Version, Content-Type. Non-ASCII names and subjects are RFC 2047 encoded.
//   PR_CLIENT_SUBMIT_TIME is the Date; PR_MESSAGE_DELIVERY_TIME is the Date plus 3 seconds.
//
// Deterministic: no clock, no randomness. CFB timestamps are zero. Directory siblings form a
// balanced red-black tree. Empty streams start at ENDOFCHAIN. Every write is read back and checked.

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import CFB from 'cfb';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..', '..');

// ---------------------------------------------------------------- MAPI constants

const PT_LONG = 0x0003;
const PT_BOOLEAN = 0x000b;
const PT_UNICODE = 0x001f;
const PT_SYSTIME = 0x0040;
const PT_BINARY = 0x0102;

// Property ids, named as in MAPI (MS-OXPROPS gives the PidTag names).
const PR = {
  IMPORTANCE: 0x0017,
  MESSAGE_CLASS: 0x001a,
  SENSITIVITY: 0x0036,
  SUBJECT: 0x0037,
  CLIENT_SUBMIT_TIME: 0x0039,
  SUBJECT_PREFIX: 0x003d,
  SENT_REPRESENTING_NAME: 0x0042,
  SENT_REPRESENTING_ADDRTYPE: 0x0064,
  SENT_REPRESENTING_EMAIL_ADDRESS: 0x0065,
  CONVERSATION_TOPIC: 0x0070,
  TRANSPORT_MESSAGE_HEADERS: 0x007d,
  RECIPIENT_TYPE: 0x0c15,
  SENDER_NAME: 0x0c1a,
  SENDER_ADDRTYPE: 0x0c1e,
  SENDER_EMAIL_ADDRESS: 0x0c1f,
  DISPLAY_BCC: 0x0e02,
  DISPLAY_CC: 0x0e03,
  DISPLAY_TO: 0x0e04,
  MESSAGE_DELIVERY_TIME: 0x0e06,
  MESSAGE_FLAGS: 0x0e07,
  HASATTACH: 0x0e1b,
  NORMALIZED_SUBJECT: 0x0e1d,
  ATTACH_SIZE: 0x0e20,
  ATTACH_NUM: 0x0e21,
  OBJECT_TYPE: 0x0ffe,
  BODY: 0x1000,
  INTERNET_MESSAGE_ID: 0x1035,
  INTERNET_REFERENCES: 0x1039,
  IN_REPLY_TO_ID: 0x1042,
  ROWID: 0x3000,
  DISPLAY_NAME: 0x3001,
  ADDRTYPE: 0x3002,
  EMAIL_ADDRESS: 0x3003,
  CREATION_TIME: 0x3007,
  LAST_MODIFICATION_TIME: 0x3008,
  STORE_SUPPORT_MASK: 0x340d,
  ATTACH_DATA_BIN: 0x3701,
  ATTACH_EXTENSION: 0x3703,
  ATTACH_FILENAME: 0x3704,
  ATTACH_METHOD: 0x3705,
  ATTACH_LONG_FILENAME: 0x3707,
  RENDERING_POSITION: 0x370b,
  ATTACH_MIME_TAG: 0x370e,
  DISPLAY_TYPE: 0x3900,
  SMTP_ADDRESS: 0x39fe,
  TRANSMITABLE_DISPLAY_NAME: 0x3a20,
  INTERNET_CPID: 0x3fde,
  SENDER_SMTP_ADDRESS: 0x5d01,
  SENT_REPRESENTING_SMTP_ADDRESS: 0x5d02,
};

const PROPATTR_READABLE_WRITABLE = 0x00000006;
const MAPI_TO = 1;
const MAPI_CC = 2;
const MAPI_MAILUSER = 6;
const MAPI_ATTACH = 7;
const DT_MAILUSER = 0;
const ATTACH_BY_VALUE = 1;
const MSGFLAG_READ = 0x01;
const MSGFLAG_HASATTACH = 0x10;
const STORE_UNICODE_OK = 0x00040000;
const IMPORTANCE_NORMAL = 1;
const SENSITIVITY_NONE = 0;
const CP_UTF8 = 65001;
const DELIVERY_LAG_SECONDS = 3;

// ---------------------------------------------------------------- CFB constants

const MSG_ROOT_CLSID = '0b0d020000000000c000000000000046'; // {00020D0B-0000-0000-C000-000000000046}
const ENDOFCHAIN = -2; // written by cfb as FE FF FF FF
const RED = 0;
const BLACK = 1;
const CFB_SEED = '\u0001Sh33tJ5';

// cfb 1.2.2 seeds a "\u0001Sh33tJ5" placeholder stream into every container it builds: its
// seed_cfb() skips the seed only when CFB.find() already finds one. A .msg must hold MS-OXMSG
// entries only, so report the seed as present. Pinned to cfb 1.2.2; read-back below confirms.
const cfbFind = CFB.find;
CFB.find = (cfb, p) => (p === `/${CFB_SEED}` ? true : cfbFind(cfb, p));

class SpecError extends Error {}

// ---------------------------------------------------------------- property bags

class PropertyBag {
  // header: the bytes before the 16-byte property entries (32 for the message, 8 otherwise).
  constructor(header) {
    this.header = header;
    this.props = new Map();
  }

  set(id, type, value) {
    this.props.set(((id << 16) | type) >>> 0, { id, type, value });
    return this;
  }

  str(id, text) {
    return this.set(id, PT_UNICODE, Buffer.from(String(text), 'utf16le'));
  }

  bin(id, data) {
    return this.set(id, PT_BINARY, Buffer.from(data));
  }

  long(id, n) {
    return this.set(id, PT_LONG, n >>> 0);
  }

  bool(id, flag) {
    return this.set(id, PT_BOOLEAN, flag ? 1 : 0);
  }

  time(id, filetime) {
    return this.set(id, PT_SYSTIME, filetime);
  }

  // Sum of the value sizes of all properties, as PR_ATTACH_SIZE counts them.
  valueBytes() {
    let total = 0;
    for (const { type, value } of this.props.values()) {
      if (type === PT_UNICODE) total += value.length + 2;
      else if (type === PT_BINARY) total += value.length;
      else if (type === PT_SYSTIME) total += 8;
      else if (type === PT_BOOLEAN) total += 2;
      else total += 4;
    }
    return total;
  }

  // [{name, data}]: the property stream first, then one stream per variable-length value.
  streams() {
    const tags = [...this.props.keys()].sort((a, b) => a - b);
    const entries = [];
    const out = [];
    for (const tag of tags) {
      const { id, type, value } = this.props.get(tag);
      const entry = Buffer.alloc(16);
      entry.writeUInt32LE(tag, 0);
      entry.writeUInt32LE(PROPATTR_READABLE_WRITABLE, 4);
      switch (type) {
        case PT_LONG:
        case PT_BOOLEAN:
          entry.writeUInt32LE(value, 8);
          break;
        case PT_SYSTIME:
          entry.writeBigUInt64LE(value, 8);
          break;
        case PT_UNICODE:
          entry.writeUInt32LE(value.length + 2, 8);
          out.push({ name: streamName(id, type), data: value });
          break;
        case PT_BINARY:
          entry.writeUInt32LE(value.length, 8);
          out.push({ name: streamName(id, type), data: value });
          break;
        default:
          throw new Error(`unsupported property type 0x${hex4(type)}`);
      }
      entries.push(entry);
    }
    return [{ name: '__properties_version1.0', data: Buffer.concat([this.header, ...entries]) }, ...out];
  }
}

function hex4(n) {
  return n.toString(16).toUpperCase().padStart(4, '0');
}

function streamName(id, type) {
  return `__substg1.0_${hex4(id)}${hex4(type)}`;
}

function storageId(n) {
  return n.toString(16).toUpperCase().padStart(8, '0');
}

// ---------------------------------------------------------------- spec parsing

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const DATE_RE =
  /^(?:(Mon|Tue|Wed|Thu|Fri|Sat|Sun), )?(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4}) (\d{2}):(\d{2}):(\d{2}) ([+-])(\d{2})(\d{2})$/;

// RFC 2822 date with numeric offset -> UTC milliseconds.
function parseDate(text) {
  const m = DATE_RE.exec(String(text));
  if (!m) throw new SpecError(`date must look like "Wed, 28 Oct 2026 09:10:00 +0100": ${text}`);
  const [, weekday, day, mon, year, hh, mi, ss, sign, oh, om] = m;
  const local = Date.UTC(+year, MONTHS.indexOf(mon), +day, +hh, +mi, +ss);
  const d = new Date(local);
  if (d.getUTCDate() !== +day || +hh > 23 || +mi > 59 || +ss > 59) throw new SpecError(`no such date: ${text}`);
  if (weekday && WEEKDAYS[d.getUTCDay()] !== weekday) {
    throw new SpecError(`${text}: ${day} ${mon} ${year} is a ${WEEKDAYS[d.getUTCDay()]}`);
  }
  const offsetMinutes = (sign === '-' ? -1 : 1) * (+oh * 60 + +om);
  return local - offsetMinutes * 60000;
}

function filetime(utcMs) {
  return (BigInt(utcMs) + 11644473600000n) * 10000n;
}

function messageId(value, field) {
  const bare = String(value).trim().replace(/^<(.*)>$/, '$1');
  if (!/^[^\s<>@]+@[^\s<>@]+$/.test(bare)) throw new SpecError(`${field} is not a message id: ${value}`);
  return `<${bare}>`;
}

function address(value, field) {
  if (!value || typeof value !== 'object' || !/^[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+$/.test(value.address || '')) {
    throw new SpecError(`${field} needs {name, address} with a valid address`);
  }
  return { name: String(value.name || '').trim(), address: value.address };
}

function bodyText(body) {
  const text = Array.isArray(body) ? body.join('\n') : String(body ?? '');
  const lf = text.replace(/\r\n?/g, '\n').replace(/\n+$/, '');
  return lf ? `${lf}\n`.replace(/\n/g, '\r\n') : '';
}

function readSpec(file) {
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (err) {
    throw new SpecError(`cannot read spec: ${err.message}`);
  }
  for (const key of ['from', 'to', 'subject', 'date', 'message_id']) {
    if (raw[key] === undefined) throw new SpecError(`missing field "${key}"`);
  }
  const to = (raw.to || []).map((a, i) => address(a, `to[${i}]`));
  if (!to.length) throw new SpecError('"to" needs at least one recipient');
  const refs = Array.isArray(raw.references)
    ? raw.references
    : String(raw.references || '').split(/\s+/).filter(Boolean);
  const attachments = (raw.attachments || []).map((a, i) => {
    if (!a || !a.path || !a.mime) throw new SpecError(`attachments[${i}] needs path and mime`);
    const source = path.resolve(ROOT, a.path);
    if (!fs.existsSync(source)) throw new SpecError(`attachments[${i}]: no file ${a.path}`);
    return { name: a.name || path.basename(a.path), mime: a.mime, data: fs.readFileSync(source) };
  });
  return {
    out: raw.out ? path.resolve(ROOT, raw.out) : null,
    from: address(raw.from, 'from'),
    to,
    cc: (raw.cc || []).map((a, i) => address(a, `cc[${i}]`)),
    subject: String(raw.subject),
    date: String(raw.date),
    utcMs: parseDate(raw.date),
    messageId: messageId(raw.message_id, 'message_id'),
    inReplyTo: raw.in_reply_to ? messageId(raw.in_reply_to, 'in_reply_to') : '',
    references: refs.map((r) => messageId(r, 'references')),
    body: bodyText(raw.body),
    attachments,
  };
}

// ---------------------------------------------------------------- RFC 5322 header block

// RFC 2047 "B" encoded words, each at most 75 characters, split on character boundaries.
function encodedWords(text) {
  const words = [];
  let chunk = '';
  for (const ch of text) {
    if (Buffer.byteLength(chunk + ch, 'utf8') > 45) {
      words.push(chunk);
      chunk = ch;
    } else {
      chunk += ch;
    }
  }
  if (chunk) words.push(chunk);
  return words.map((w) => `=?utf-8?B?${Buffer.from(w, 'utf8').toString('base64')}?=`).join(' ');
}

function headerText(text) {
  return /[^\x20-\x7e]/.test(text) ? encodedWords(text) : text;
}

function mailbox({ name, address: addr }) {
  if (!name || name === addr) return addr;
  if (/[^\x20-\x7e]/.test(name)) return `${encodedWords(name)} <${addr}>`;
  if (/[()<>[\]:;@\\,."]/.test(name)) return `"${name.replace(/(["\\])/g, '\\$1')}" <${addr}>`;
  return `${name} <${addr}>`;
}

// Fold at spaces so that lines stay within 78 characters where the words allow it.
function header(name, value) {
  const lines = [];
  let line = `${name}:`;
  for (const word of value.split(' ')) {
    if (line.length + 1 + word.length > 78 && line.length > name.length + 1) {
      lines.push(line);
      line = ` ${word}`;
    } else {
      line += ` ${word}`;
    }
  }
  lines.push(line);
  return lines.join('\r\n');
}

function transportHeaders(msg) {
  const lines = [
    header('From', mailbox(msg.from)),
    header('To', msg.to.map(mailbox).join(', ')),
  ];
  if (msg.cc.length) lines.push(header('Cc', msg.cc.map(mailbox).join(', ')));
  lines.push(header('Subject', headerText(msg.subject)));
  lines.push(`Date: ${msg.date}`);
  lines.push(`Message-ID: ${msg.messageId}`);
  if (msg.inReplyTo) lines.push(`In-Reply-To: ${msg.inReplyTo}`);
  if (msg.references.length) lines.push(header('References', msg.references.join(' ')));
  lines.push('MIME-Version: 1.0');
  if (msg.attachments.length) {
    const token = crypto.createHash('sha1').update(msg.messageId).digest('hex').slice(0, 24).toUpperCase();
    lines.push(`Content-Type: multipart/mixed; boundary="_002_${token}_"`);
  } else {
    lines.push('Content-Type: text/plain; charset="utf-8"');
    lines.push(`Content-Transfer-Encoding: ${/[^\x00-\x7f]/.test(msg.body) ? 'quoted-printable' : '7bit'}`);
  }
  return `${lines.join('\r\n')}\r\n`;
}

// ---------------------------------------------------------------- message assembly

// Outlook's rule: a prefix is 1 to 3 non-digit characters, a colon and a space ("RE: ").
function splitSubject(subject) {
  const m = /^([^\d\s:]{1,3}: )(.*)$/s.exec(subject);
  return m ? { prefix: m[1], normalized: m[2] } : { prefix: '', normalized: subject };
}

// 8.3 name for PR_ATTACH_FILENAME; long names become ABCDEF~1.EXT.
function shortName(name) {
  const dot = name.lastIndexOf('.');
  const base = dot > 0 ? name.slice(0, dot) : name;
  const ext = dot > 0 ? name.slice(dot + 1) : '';
  const ok = /^[A-Za-z0-9_\-!#$%&'(){}^~@`]+$/;
  if (base.length <= 8 && ext.length <= 3 && ok.test(base) && (!ext || ok.test(ext))) return name;
  const clean = (s) => s.toUpperCase().replace(/[^A-Z0-9_\-!#$%&'(){}^~@`]/g, '');
  const ext3 = clean(ext).slice(0, 3);
  return `${clean(base).slice(0, 6) || 'ATTACH'}~1${ext3 ? `.${ext3}` : ''}`;
}

function recipientBag(rcpt, row, type) {
  const name = rcpt.name || rcpt.address;
  return new PropertyBag(Buffer.alloc(8))
    .long(PR.ROWID, row)
    .long(PR.RECIPIENT_TYPE, type)
    .long(PR.OBJECT_TYPE, MAPI_MAILUSER)
    .long(PR.DISPLAY_TYPE, DT_MAILUSER)
    .str(PR.DISPLAY_NAME, name)
    .str(PR.TRANSMITABLE_DISPLAY_NAME, name)
    .str(PR.ADDRTYPE, 'SMTP')
    .str(PR.EMAIL_ADDRESS, rcpt.address)
    .str(PR.SMTP_ADDRESS, rcpt.address);
}

function attachmentBag(att, num, ft) {
  const bag = new PropertyBag(Buffer.alloc(8))
    .long(PR.ATTACH_NUM, num)
    .long(PR.OBJECT_TYPE, MAPI_ATTACH)
    .long(PR.ATTACH_METHOD, ATTACH_BY_VALUE)
    .long(PR.RENDERING_POSITION, 0xffffffff)
    .time(PR.CREATION_TIME, ft)
    .time(PR.LAST_MODIFICATION_TIME, ft)
    .bin(PR.ATTACH_DATA_BIN, att.data)
    .str(PR.ATTACH_FILENAME, shortName(att.name))
    .str(PR.ATTACH_LONG_FILENAME, att.name)
    .str(PR.ATTACH_EXTENSION, path.extname(att.name))
    .str(PR.ATTACH_MIME_TAG, att.mime)
    .str(PR.DISPLAY_NAME, att.name);
  return bag.long(PR.ATTACH_SIZE, bag.valueBytes() + 4); // + 4: PR_ATTACH_SIZE itself
}

function messageBag(msg, recipientCount) {
  const header = Buffer.alloc(32);
  header.writeUInt32LE(recipientCount, 8); // next recipient id
  header.writeUInt32LE(msg.attachments.length, 12); // next attachment id
  header.writeUInt32LE(recipientCount, 16); // recipient count
  header.writeUInt32LE(msg.attachments.length, 20); // attachment count

  const submitted = filetime(msg.utcMs);
  const delivered = filetime(msg.utcMs + DELIVERY_LAG_SECONDS * 1000);
  const senderName = msg.from.name || msg.from.address;
  const { prefix, normalized } = splitSubject(msg.subject);
  const names = (list) => list.map((r) => r.name || r.address).join('; ');
  const hasAttach = msg.attachments.length > 0;

  const bag = new PropertyBag(header)
    .str(PR.MESSAGE_CLASS, 'IPM.Note')
    .str(PR.SUBJECT, msg.subject)
    .str(PR.NORMALIZED_SUBJECT, normalized)
    .str(PR.CONVERSATION_TOPIC, normalized)
    .str(PR.BODY, msg.body)
    .str(PR.SENDER_NAME, senderName)
    .str(PR.SENDER_EMAIL_ADDRESS, msg.from.address)
    .str(PR.SENDER_ADDRTYPE, 'SMTP')
    .str(PR.SENDER_SMTP_ADDRESS, msg.from.address)
    .str(PR.SENT_REPRESENTING_NAME, senderName)
    .str(PR.SENT_REPRESENTING_EMAIL_ADDRESS, msg.from.address)
    .str(PR.SENT_REPRESENTING_ADDRTYPE, 'SMTP')
    .str(PR.SENT_REPRESENTING_SMTP_ADDRESS, msg.from.address)
    .str(PR.DISPLAY_TO, names(msg.to))
    .str(PR.DISPLAY_CC, names(msg.cc))
    .str(PR.DISPLAY_BCC, '')
    .str(PR.INTERNET_MESSAGE_ID, msg.messageId)
    .str(PR.TRANSPORT_MESSAGE_HEADERS, transportHeaders(msg))
    .time(PR.CLIENT_SUBMIT_TIME, submitted)
    .time(PR.MESSAGE_DELIVERY_TIME, delivered)
    .time(PR.CREATION_TIME, delivered)
    .time(PR.LAST_MODIFICATION_TIME, delivered)
    .long(PR.MESSAGE_FLAGS, MSGFLAG_READ | (hasAttach ? MSGFLAG_HASATTACH : 0))
    .bool(PR.HASATTACH, hasAttach)
    .long(PR.IMPORTANCE, IMPORTANCE_NORMAL)
    .long(PR.SENSITIVITY, SENSITIVITY_NONE)
    .long(PR.INTERNET_CPID, CP_UTF8)
    .long(PR.STORE_SUPPORT_MASK, STORE_UNICODE_OK);
  if (prefix) bag.str(PR.SUBJECT_PREFIX, prefix);
  if (msg.inReplyTo) bag.str(PR.IN_REPLY_TO_ID, msg.inReplyTo);
  if (msg.references.length) bag.str(PR.INTERNET_REFERENCES, msg.references.join(' '));
  return bag;
}

// Map of storage-relative path -> bytes for every stream of the .msg.
function msgStreams(msg) {
  const files = new Map();
  const add = (dir, bag) => {
    for (const { name, data } of bag.streams()) files.set(dir ? `${dir}/${name}` : name, data);
  };
  const recipients = [
    ...msg.to.map((r) => [r, MAPI_TO]),
    ...msg.cc.map((r) => [r, MAPI_CC]),
  ];
  add('', messageBag(msg, recipients.length));
  for (const name of ['__substg1.0_00020102', '__substg1.0_00030102', '__substg1.0_00040102']) {
    files.set(`__nameid_version1.0/${name}`, Buffer.alloc(0));
  }
  recipients.forEach(([rcpt, type], i) => add(`__recip_version1.0_#${storageId(i)}`, recipientBag(rcpt, i, type)));
  const attachTime = filetime(msg.utcMs);
  msg.attachments.forEach((att, i) => add(`__attach_version1.0_#${storageId(i)}`, attachmentBag(att, i, attachTime)));
  return files;
}

// ---------------------------------------------------------------- CFB container

// MS-CFB 2.6.4: shorter names sort first, then compare the upper-cased names.
function compareNames(a, b) {
  if (a.length !== b.length) return a.length - b.length;
  const ua = a.toUpperCase();
  const ub = b.toUpperCase();
  return ua < ub ? -1 : ua > ub ? 1 : 0;
}

function parentPath(p) {
  const trimmed = p.endsWith('/') ? p.slice(0, -1) : p;
  return trimmed.slice(0, trimmed.lastIndexOf('/') + 1);
}

// Replace cfb's sibling chains with a balanced red-black tree per storage: midpoint split,
// nodes on an incomplete last level red, all others black. Empty streams start at ENDOFCHAIN.
function relinkDirectory(cfb) {
  const index = cfb.FileIndex;
  const children = new Map();
  index.forEach((entry, i) => {
    entry.L = entry.R = entry.C = -1;
    if (entry.type === 2 && !entry.size) entry.start = ENDOFCHAIN;
    if (i === 0) return;
    const parent = parentPath(cfb.FullPaths[i]);
    if (!children.has(parent)) children.set(parent, []);
    children.get(parent).push(i);
  });
  index[0].color = BLACK;
  index.forEach((entry, i) => {
    if (entry.type !== 1 && entry.type !== 5) return;
    const kids = (children.get(cfb.FullPaths[i]) || []).sort((a, b) => compareNames(index[a].name, index[b].name));
    const fullLevels = Math.floor(Math.log2(kids.length + 1));
    const build = (lo, hi, depth) => {
      if (lo > hi) return -1;
      const mid = (lo + hi) >>> 1;
      const node = index[kids[mid]];
      node.color = depth >= fullLevels ? RED : BLACK;
      node.L = build(lo, mid - 1, depth + 1);
      node.R = build(mid + 1, hi, depth + 1);
      return kids[mid];
    };
    entry.C = build(0, kids.length - 1, 0);
  });
}

function writeCfb(files) {
  const cfb = CFB.utils.cfb_new({ CLSID: MSG_ROOT_CLSID });
  for (const [p, data] of files) CFB.utils.cfb_add(cfb, `/${p}`, data, { unsafe: true });
  CFB.utils.cfb_gc(cfb); // sort entries and create the storages
  relinkDirectory(cfb);
  return Buffer.from(CFB.write(cfb, { type: 'buffer', fileType: 'cfb' }));
}

// Black height of the subtree at i, or throw if order or colours break the red-black rules.
function checkTree(index, i, lo, hi) {
  if (i === -1) return 1;
  const node = index[i];
  if ((lo && compareNames(lo, node.name) >= 0) || (hi && compareNames(node.name, hi) >= 0)) {
    throw new Error(`directory order broken at ${node.name}`);
  }
  for (const k of [node.L, node.R]) {
    if (node.color === RED && k !== -1 && index[k].color === RED) throw new Error(`red-red at ${node.name}`);
  }
  const left = checkTree(index, node.L, lo, node.name);
  const right = checkTree(index, node.R, node.name, hi);
  if (left !== right) throw new Error(`unequal black height below ${node.name}`);
  return left + (node.color === BLACK ? 1 : 0);
}

// Read the container back and compare every stream and storage with what was meant.
function readBack(buf, files) {
  const back = CFB.read(buf, { type: 'buffer' });
  const rootPath = back.FullPaths[0];
  const want = new Set(files.keys());
  for (const p of files.keys()) {
    const parts = p.split('/');
    for (let k = 1; k < parts.length; k += 1) want.add(`${parts.slice(0, k).join('/')}/`);
  }
  const seen = new Set();
  back.FileIndex.forEach((entry, i) => {
    if (i === 0 || (entry.type !== 1 && entry.type !== 2)) return;
    const rel = back.FullPaths[i].slice(rootPath.length);
    if (!want.has(rel)) throw new Error(`unexpected entry in container: ${JSON.stringify(rel)}`);
    if (entry.type === 2) {
      const got = Buffer.from(entry.content || []).subarray(0, entry.size);
      if (!got.equals(files.get(rel))) throw new Error(`stream differs after read-back: ${rel}`);
      if (!entry.size && entry.start !== ENDOFCHAIN && entry.start !== 0xfffffffe) {
        throw new Error(`empty stream not at ENDOFCHAIN: ${rel}`);
      }
    }
    seen.add(rel);
  });
  for (const rel of want) if (!seen.has(rel)) throw new Error(`missing after read-back: ${rel}`);
  if (back.FileIndex[0].clsid !== MSG_ROOT_CLSID) throw new Error('root CLSID is not the MSG CLSID');
  back.FileIndex.forEach((entry) => {
    if (entry.type === 1 || entry.type === 5) checkTree(back.FileIndex, entry.C, '', '');
  });
}

export function buildMsg(specFile) {
  const msg = readSpec(specFile);
  const files = msgStreams(msg);
  const buf = writeCfb(files);
  readBack(buf, files);
  return { msg, buf };
}

// ---------------------------------------------------------------- command line

function usage(message) {
  if (message) console.error(`make_msg: ${message}`);
  console.error('usage: node make_msg.mjs [--check] [SPEC.json...] | node make_msg.mjs SPEC.json --out FILE.msg');
  process.exit(2);
}

function rel(p) {
  const r = path.relative(ROOT, p);
  return r.startsWith('..') || path.isAbsolute(r) ? p : r.split(path.sep).join('/');
}

function main(argv) {
  let check = false;
  let outOverride = null;
  const specs = [];
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '-h' || arg === '--help') {
      const head = fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n\n')[0];
      console.log(head.replace(/^#!.*\n/, '').replace(/^\/\/ ?/gm, ''));
      return 0;
    }
    if (arg === '--check') check = true;
    else if (arg === '--out') outOverride = argv[(i += 1)] || usage('--out needs a file');
    else if (arg.startsWith('-')) usage(`unknown option ${arg}`);
    else specs.push(arg);
  }
  if (!specs.length && !outOverride) {
    const dir = path.join(HERE, 'specs');
    specs.push(...fs.readdirSync(dir).filter((f) => f.endsWith('.json')).sort().map((f) => path.join(dir, f)));
  }
  if (!specs.length) usage('no spec given');
  if (outOverride && (specs.length !== 1 || check)) usage('--out takes exactly one spec and no --check');

  let failed = 0;
  for (const spec of specs) {
    let built;
    try {
      built = buildMsg(spec);
    } catch (err) {
      if (err instanceof SpecError) usage(`${spec}: ${err.message}`);
      throw err;
    }
    const out = outOverride ? path.resolve(outOverride) : built.msg.out;
    if (!out) usage(`${spec}: no "out" path; give --out FILE`);
    const sha = crypto.createHash('sha256').update(built.buf).digest('hex');
    if (check) {
      const same = fs.existsSync(out) && fs.readFileSync(out).equals(built.buf);
      console.log(`${same ? 'ok' : 'DIFFERS'}: ${rel(out)}`);
      if (!same) failed += 1;
    } else {
      fs.mkdirSync(path.dirname(out), { recursive: true });
      fs.writeFileSync(out, built.buf);
      console.log(`wrote ${rel(out)} (${built.buf.length} bytes, sha256 ${sha})`);
    }
  }
  return failed ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main(process.argv.slice(2));
}

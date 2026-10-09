import { readFileSync } from 'node:fs';
import { inflateSync } from 'node:zlib';

// Decode Chromium's non-interlaced 8-bit RGB/RGBA screenshots without new packages.
function readPixels(path) {
  const png = readFileSync(path);
  let width, height, channels;
  const chunks = [];
  for (let offset = 8; offset < png.length;) {
    const length = png.readUInt32BE(offset);
    const type = png.toString('ascii', offset + 4, offset + 8);
    const data = png.subarray(offset + 8, offset + 8 + length);
    if (type === 'IHDR') {
      width = data.readUInt32BE(0); height = data.readUInt32BE(4);
      if (data[8] !== 8 || ![2, 6].includes(data[9]) || data[12] !== 0) throw new Error('Unsupported screenshot encoding');
      channels = data[9] === 2 ? 3 : 4;
    }
    if (type === 'IDAT') chunks.push(data);
    offset += length + 12;
  }
  const raw = inflateSync(Buffer.concat(chunks));
  const stride = width * channels;
  const pixels = Buffer.alloc(height * stride);
  let offset = 0;
  const paeth = (a, b, c) => { const p = a + b - c; const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); return pa <= pb && pa <= pc ? a : pb <= pc ? b : c; };
  for (let y = 0; y < height; y++) {
    const filter = raw[offset++];
    if (filter > 4) throw new Error('Unsupported PNG filter');
    for (let x = 0; x < stride; x++) {
      const index = y * stride + x;
      const a = x >= channels ? pixels[index - channels] : 0;
      const b = y > 0 ? pixels[index - stride] : 0;
      const c = y > 0 && x >= channels ? pixels[index - stride - channels] : 0;
      pixels[index] = (raw[offset++] + [0, a, b, Math.floor((a + b) / 2), paeth(a, b, c)][filter]) & 255;
    }
  }
  return (x, y) => {
    const index = (Math.min(height - 1, Math.max(0, Math.round(y))) * width + Math.min(width - 1, Math.max(0, Math.round(x)))) * channels;
    return [...pixels.subarray(index, index + 3)];
  };
}
const luminance = (rgb) => rgb.map((value) => value / 255).map((v) => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4).reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
export function contrastMeasurements(path, samples) {
  const pixel = readPixels(path);
  return samples.map(({ selector, color, x, y }) => {
    const background = pixel(x, y);
    const foreground = color.match(/[\d.]+/g).slice(0, 3).map(Number);
    const l1 = luminance(foreground), l2 = luminance(background);
    return { selector, foreground, background, ratio: +((Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05)).toFixed(2), x, y };
  });
}

// Is a camera frame good enough to describe? Checked in the page, before the frame is sent.
//
// A blind user cannot see that the picture is black or smeared, and the model will still
// answer it, confidently. So a frame that is too dark or almost uniform (lens covered) is
// not sent at all, and a blurred one is described with a warning that it is blurred.
// Pure functions, so they can be unit-tested.
//
// The limits were set on the 65 evaluation images, shrunk to this width: no real photo is
// below any of them, while darkened copies (12% brightness) and strongly blurred copies
// (9x9 box blur) all are. Real photos measured brightness >= 49, contrast >= 10 and
// sharpness >= 129; darkened copies brightness <= 31 and contrast <= 10; blurred copies
// sharpness <= 31.

export const QUALITY_WIDTH = 160;  // the frame is shrunk to this width before measuring

export const LIMITS = {
  dark: 35,          // mean brightness (0-255) below this, and
  darkContrast: 15,  // contrast below this: too dark. A night street with bright lights
                     // has more contrast and is still described.
  uniform: 5,        // contrast (standard deviation) below this: nothing to see
  blurry: 50,        // sharpness (variance of the Laplacian) below this: blurred
};

// Brightness, contrast and sharpness of a grey image, one byte per pixel.
export function frameStats(gray, width, height) {
  const n = width * height;
  let sum = 0;
  for (let i = 0; i < n; i++) sum += gray[i];
  const mean = sum / n;
  let spread = 0;
  for (let i = 0; i < n; i++) spread += (gray[i] - mean) ** 2;
  // Sharp edges give large second derivatives; blur flattens them.
  let lapSum = 0, lapSquares = 0, count = 0;
  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const i = y * width + x;
      const lap = 4 * gray[i] - gray[i - 1] - gray[i + 1] - gray[i - width] - gray[i + width];
      lapSum += lap;
      lapSquares += lap * lap;
      count++;
    }
  }
  const lapMean = count ? lapSum / count : 0;
  return {
    brightness: mean,
    contrast: Math.sqrt(spread / n),
    sharpness: count ? lapSquares / count - lapMean ** 2 : 0,
  };
}

// "dark" and "uniform" frames are not worth sending; "blurry" ones are sent with a warning.
export function judgeFrame({ brightness, contrast, sharpness }, limits = LIMITS) {
  if (brightness < limits.dark && contrast < limits.darkContrast) return "dark";
  if (contrast < limits.uniform) return "uniform";
  if (sharpness < limits.blurry) return "blurry";
  return "ok";
}

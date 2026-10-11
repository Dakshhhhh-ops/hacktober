// Frame-change gating for automatic monitoring.
//
// This is a performance optimisation, NOT a safety mechanism: a small change in the
// picture can still be a new hazard. Pure functions, so they can be unit-tested.

export const THUMB_SIZE = 16;

// RGBA pixel data -> one grey value (0-255) per pixel.
export function toGray(rgba) {
  const gray = new Uint8Array(rgba.length / 4);
  for (let i = 0; i < gray.length; i++) {
    gray[i] = Math.round(0.299 * rgba[i * 4] + 0.587 * rgba[i * 4 + 1] + 0.114 * rgba[i * 4 + 2]);
  }
  return gray;
}

// Mean absolute difference between two grey thumbnails, 0-255.
// With no previous frame the scene counts as fully changed.
export function frameDifference(previous, current) {
  if (!previous || previous.length !== current.length) return 255;
  let total = 0;
  for (let i = 0; i < current.length; i++) total += Math.abs(current[i] - previous[i]);
  return total / current.length;
}

// Should an automatic frame be sent to the model now?
export function shouldDescribe({ difference, threshold, msSinceLast, minIntervalMs, busy }) {
  if (busy) return false;
  if (msSinceLast < minIntervalMs) return false;
  return difference >= threshold;
}

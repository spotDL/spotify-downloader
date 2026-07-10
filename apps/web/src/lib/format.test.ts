import { describe, expect, it } from "vitest";
import { formatDuration, formatFollowers, joinArtists, joinMeta } from "./format";

describe("formatDuration", () => {
  it("formats milliseconds as m:ss", () => {
    expect(formatDuration(248_000)).toBe("4:08");
  });
  it("renders an em dash for null/negative", () => {
    expect(formatDuration(null)).toBe("—");
    expect(formatDuration(-1)).toBe("—");
  });
});

describe("formatFollowers", () => {
  it("compacts large counts with a K/M/B suffix", () => {
    expect(formatFollowers(33_901_227)).toBe("33.9M");
    expect(formatFollowers(58_400_000)).toBe("58.4M");
    expect(formatFollowers(1_234)).toBe("1.2K");
    expect(formatFollowers(2_500_000_000)).toBe("2.5B");
  });
  it("leaves sub-thousand counts untouched", () => {
    expect(formatFollowers(842)).toBe("842");
    expect(formatFollowers(0)).toBe("0");
  });
  it("drops a trailing .0", () => {
    expect(formatFollowers(1_000_000)).toBe("1M");
  });
  it("rounds to a whole number at/above 100 of a unit", () => {
    expect(formatFollowers(123_400_000)).toBe("123M");
  });
  it("renders an em dash for null/negative", () => {
    expect(formatFollowers(null)).toBe("—");
    expect(formatFollowers(undefined)).toBe("—");
    expect(formatFollowers(-5)).toBe("—");
  });
});

describe("joinArtists / joinMeta", () => {
  it("joins artists with a comma", () => {
    expect(joinArtists(["A", "B"])).toBe("A, B");
  });
  it("joins truthy meta parts with a middle dot", () => {
    expect(joinMeta([2013, null, "12 tracks", ""])).toBe("2013 · 12 tracks");
  });
});

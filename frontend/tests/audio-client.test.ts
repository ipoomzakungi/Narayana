import { describe, expect, it } from "vitest";

import { floatToPcm16Base64 } from "@/lib/audio-client";

describe("audio-client", () => {
  it("converts float samples to pcm16 base64", () => {
    const encoded = floatToPcm16Base64(new Float32Array([-1, 0, 1]));
    const binary = atob(encoded);

    expect(binary.length).toBe(6);
  });
});

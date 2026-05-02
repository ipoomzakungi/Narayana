export interface PcmFrame {
  sequence: number;
  timestamp_ms: number;
  encoding: "pcm16";
  sample_rate_hz: number;
  channels: 1;
  duration_ms: 20;
  audio_base64: string;
}

export function floatToPcm16Base64(samples: Float32Array): string {
  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);
  samples.forEach((sample, index) => {
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(index * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  });
  const bytes = new Uint8Array(buffer);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
}

export async function startMicStreaming(onFrame: (frame: PcmFrame) => void): Promise<() => void> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      noiseSuppression: true,
      echoCancellation: true
    }
  });
  const context = new AudioContext({ sampleRate: 16000 });
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(1024, 1, 1);
  let sequence = 0;
  let carry = new Float32Array(0);
  const frameSamples = 320;

  processor.onaudioprocess = (event) => {
    const input = event.inputBuffer.getChannelData(0);
    const merged = new Float32Array(carry.length + input.length);
    merged.set(carry);
    merged.set(input, carry.length);

    let offset = 0;
    while (offset + frameSamples <= merged.length) {
      const chunk = merged.slice(offset, offset + frameSamples);
      sequence += 1;
      onFrame({
        sequence,
        timestamp_ms: sequence * 20,
        encoding: "pcm16",
        sample_rate_hz: context.sampleRate,
        channels: 1,
        duration_ms: 20,
        audio_base64: floatToPcm16Base64(chunk)
      });
      offset += frameSamples;
    }
    carry = merged.slice(offset);
  };

  source.connect(processor);
  processor.connect(context.destination);

  return () => {
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    void context.close();
  };
}

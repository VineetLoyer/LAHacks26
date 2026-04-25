import { NextResponse } from "next/server";
import { signRequest } from "@worldcoin/idkit/signing";

export async function GET() {
  const signingKey = process.env.WORLD_RP_SIGNING_KEY;
  const rpId = process.env.WORLD_RP_ID;
  const action = process.env.NEXT_PUBLIC_WORLD_ACTION || "verify-human";

  if (!signingKey || !rpId) {
    return NextResponse.json(
      { error: "World ID RP signing not configured" },
      { status: 503 }
    );
  }

  try {
    const { sig, nonce, createdAt, expiresAt } = signRequest({
      signingKeyHex: signingKey,
      action,
      ttl: 300,
    });

    return NextResponse.json({
      rp_id: rpId,
      nonce,
      created_at: createdAt,
      expires_at: expiresAt,
      signature: sig,
    });
  } catch (error) {
    console.error("Failed to sign World ID request:", error);
    return NextResponse.json(
      { error: "Failed to generate RP context" },
      { status: 500 }
    );
  }
}

precision mediump float;
uniform vec4 u_Color;

void main() {
    // gl_PointCoord is [0,1] across the point square; disc mask centered at 0.5
    vec2 coord = gl_PointCoord - vec2(0.5);
    float dist = dot(coord, coord); // squared distance from centre
    if (dist > 0.25) discard;      // outside circle radius 0.5
    float alpha = smoothstep(0.25, 0.20, dist); // soft antialiased edge
    gl_FragColor = vec4(u_Color.rgb, u_Color.a * alpha);
}

attribute vec3 a_Position;
uniform mat4 u_ModelViewProjection;
uniform float u_PointSize;

void main() {
    gl_Position = u_ModelViewProjection * vec4(a_Position, 1.0);
    // Perspective-correct: constant world-space dot size
    gl_PointSize = u_PointSize / gl_Position.w;
}

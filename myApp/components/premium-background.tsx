import React from 'react';
import { StyleSheet, View, Dimensions } from 'react-native';
import Svg, { Line, Circle, Defs, RadialGradient, Stop, Rect } from 'react-native-svg';
import { Colors } from '../constants/theme';
import { useColorScheme } from '../hooks/use-color-scheme';

const { width, height } = Dimensions.get('window');

// Generate a static web-mesh of nodes and connections
const generateMesh = () => {
  const nodes = [];
  const lines = [];
  const nodeCount = 15;
  
  // Create nodes
  for (let i = 0; i < nodeCount; i++) {
    nodes.push({
      x: Math.random() * width,
      y: Math.random() * (height * 0.6),
      size: Math.random() * 2 + 1,
    });
  }
  
  // Create connections for nearby nodes
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dist = Math.sqrt(
        Math.pow(nodes[i].x - nodes[j].x, 2) + 
        Math.pow(nodes[i].y - nodes[j].y, 2)
      );
      if (dist < 150) {
        lines.push({ i, j, opacity: 1 - dist / 150 });
      }
    }
  }
  
  return { nodes, lines };
};

const mesh = generateMesh();

export default function PremiumBackground({ children }: { children: React.ReactNode }) {
  const colorScheme = useColorScheme() ?? 'dark';
  const isDark = colorScheme === 'dark';

  return (
    <View style={[styles.container, { backgroundColor: Colors[colorScheme].background }]}>
      {isDark && (
        <>
          {/* Background Glow Blobs */}
          <View style={[styles.glow, styles.glowLeft, { backgroundColor: 'rgba(0, 229, 255, 0.08)' }]} />
          <View style={[styles.glow, styles.glowRight, { backgroundColor: 'rgba(191, 90, 242, 0.1)' }]} />
          
          {/* The WebMesh Overlay */}
          <View style={StyleSheet.absoluteFill}>
            <Svg height={height} width={width}>
              <Defs>
                <RadialGradient id="grad" cx="50%" cy="50%" rx="50%" ry="50%">
                  <Stop offset="0%" stopColor="#00e5ff" stopOpacity="0.1" />
                  <Stop offset="100%" stopColor="#00e5ff" stopOpacity="0" />
                </RadialGradient>
              </Defs>
              
              {/* Grid Dots */}
              {Array.from({ length: 15 }).map((_, i) => 
                Array.from({ length: 10 }).map((_, j) => (
                  <Circle 
                    key={`dot-${i}-${j}`}
                    cx={(width / 10) * j} 
                    cy={(height / 15) * i} 
                    r="0.5" 
                    fill="rgba(77, 148, 255, 0.15)" 
                  />
                ))
              )}

              {/* Mesh Lines */}
              {mesh.lines.map((l, idx) => (
                <Line
                  key={`line-${idx}`}
                  x1={mesh.nodes[l.i].x}
                  y1={mesh.nodes[l.i].y}
                  x2={mesh.nodes[l.j].x}
                  y2={mesh.nodes[l.j].y}
                  stroke="#00e5ff"
                  strokeWidth="0.5"
                  strokeOpacity={l.opacity * 0.15}
                />
              ))}

              {/* Mesh Nodes */}
              {mesh.nodes.map((n, idx) => (
                <Circle
                  key={`node-${idx}`}
                  cx={n.x}
                  cy={n.y}
                  r={n.size}
                  fill="#00e5ff"
                  opacity={0.2}
                />
              ))}
            </Svg>
          </View>
        </>
      )}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  glow: {
    position: 'absolute',
    width: width * 1.5,
    height: width * 1.5,
    borderRadius: width * 0.75,
    opacity: 0.6,
  },
  glowLeft: {
    top: -width * 0.3,
    left: -width * 0.5,
  },
  glowRight: {
    top: height * 0.05,
    right: -width * 0.6,
  },
});

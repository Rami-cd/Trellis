import { motion } from 'motion/react';

const SLAM_EASE = Array(32).fill(0).map((_, i) => {
  const mod = i % 4;
  if (mod === 0) return "easeIn";
  if (mod === 1) return "circOut";
  if (mod === 2) return "easeOut";
  return "easeIn";
});

const SLAM_TIMES = [
  0, 0.02, 0.04, 0.07,
  0.125, 0.135, 0.155, 0.185,
  0.25, 0.26, 0.28, 0.31,
  0.375, 0.385, 0.405, 0.435,
  0.5, 0.51, 0.53, 0.56,
  0.625, 0.635, 0.655, 0.685,
  0.75, 0.76, 0.78, 0.81,
  0.875, 0.885, 0.905, 0.935,
  1,
];

// Each notch: slow crawl → overshoot → snap back
const RING_KEYFRAMES   = [0,2,5,52,45,47,50,97,90,92,95,142,135,137,140,187,180,182,185,232,225,227,230,277,270,272,275,322,315,317,320,367,360];
const WHEEL_KEYFRAMES  = [25,27,30,77,70,72,75,122,115,117,120,167,160,162,165,212,205,207,210,257,250,252,255,302,295,297,300,347,340,342,345,392,385];

const TRANSITION = {
  duration: 9.5,
  repeat: Infinity,
  times: [0, 0.06, 0.09, 0.092, 0.125],
  ease: SLAM_EASE,
};

export default function LoadingWheel({ size = 200 }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        perspective: 350,
      }}
    >
      {/* Glow ring */}
      <motion.div
        animate={{ rotateZ: RING_KEYFRAMES }}
        transition={TRANSITION}
        style={{
          position: 'absolute',
          width: '75%',
          height: '75%',
          borderRadius: '50%',
          border: '1px solid rgba(227,239,38,0.15)',
          // CHANGED: Dynamic blur that scales with the component size
          filter: `blur(${size * 0.015}px)`, 
          rotateX: 45,
        }}
      />

      {/* Wheel */}
      <motion.svg
        viewBox="0 0 100 100"
        animate={{ rotateZ: WHEEL_KEYFRAMES }}
        transition={TRANSITION}
        style={{
          width: '55%',
          height: '55%',
          rotateX: 45,
          originX: '50%',
          originY: '50%',
        }}
      >
        <g>
          {[...Array(8)].map((_, index) => (
            <motion.g
              key={index}
              transform={`rotate(${index * 45} 50 50)`}
              animate={{ opacity: [0.25, 1, 0.25] }}
              transition={{
                duration: 2.5,
                delay: index * 0.15,
                repeat: Infinity,
                ease: 'linear',
              }}
            >
              <line
                x1="50" y1="45" x2="50" y2="15"
                stroke="#E3EF26"
                vectorEffect="non-scaling-stroke"
                strokeWidth="2.8"
                strokeLinecap="round"
              />
              <circle
                cx="50" cy="9" r="5.5"
                fill="none"
                stroke="#E3EF26"
                vectorEffect="non-scaling-stroke"
                strokeWidth="2.2"
              />
            </motion.g>
          ))}
        </g>

        <circle
          cx="50" cy="50" r="5"
          stroke="#E3EF26"
          vectorEffect="non-scaling-stroke"
          strokeWidth="2.5"
          fill="none"
        />
        <circle
          cx="50" cy="50" r="27"
          fill="none"
          stroke="#E3EF26"
          vectorEffect="non-scaling-stroke"
          strokeWidth="3.4"
          opacity="0.7"
        />
      </motion.svg>
    </div>
  );
}
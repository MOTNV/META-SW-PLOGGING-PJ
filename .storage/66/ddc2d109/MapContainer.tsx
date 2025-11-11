import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';

interface MapContainerProps {
  location?: {
    latitude: number;
    longitude: number;
  };
  route?: Array<{
    latitude: number;
    longitude: number;
    timestamp: string;
  }>;
  onMapReady?: () => void;
  style?: any;
}

export default function MapContainer({ 
  location, 
  route, 
  onMapReady, 
  style 
}: MapContainerProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    if (Platform.OS === 'web' && mapContainerRef.current) {
      // 맵 컨테이너가 준비되면 콜백 호출
      setMapReady(true);
      onMapReady?.();
    }
  }, [onMapReady]);

  if (Platform.OS === 'web') {
    return (
      <div 
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '100%',
          backgroundColor: '#f0f0f0',
          border: '2px dashed #ccc',
          borderRadius: '8px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          ...style
        }}
      >
        <div style={{
          textAlign: 'center',
          color: '#666',
          fontSize: '16px',
          fontWeight: 'bold',
          marginBottom: '10px'
        }}>
          🗺️ 맵 API 연동 영역
        </div>
        
        <div style={{
          textAlign: 'center',
          color: '#888',
          fontSize: '14px',
          maxWidth: '300px',
          lineHeight: '1.5'
        }}>
          여기에 카카오맵 또는 네이버 맵 API를 연동하세요
        </div>

        {location && (
          <div style={{
            position: 'absolute',
            top: '10px',
            left: '10px',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#333',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}>
            📍 현재 위치: {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}
          </div>
        )}

        {route && route.length > 0 && (
          <div style={{
            position: 'absolute',
            top: '10px',
            right: '10px',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#333',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}>
            🛤️ 경로 포인트: {route.length}개
          </div>
        )}

        <div style={{
          marginTop: '20px',
          padding: '12px 16px',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          border: '1px solid rgba(76, 175, 80, 0.3)',
          borderRadius: '6px',
          fontSize: '12px',
          color: '#2e7d32',
          maxWidth: '350px'
        }}>
          <strong>연동 가이드:</strong><br/>
          • 카카오맵: Kakao Maps API 사용<br/>
          • 네이버맵: NAVER Maps API 사용<br/>
          • 이 컴포넌트를 원하는 맵 라이브러리로 교체하세요
        </div>
      </div>
    );
  }

  // 네이티브 앱에서는 기본 뷰 반환
  return (
    <View style={[styles.container, style]}>
      <View style={styles.placeholder}>
        <Text style={styles.placeholderTitle}>🗺️ 맵 영역</Text>
        <Text style={styles.placeholderText}>
          네이티브 앱에서는 React Native Maps 또는{'\n'}
          원하는 맵 라이브러리를 사용하세요
        </Text>
        
        {location && (
          <View style={styles.locationInfo}>
            <Text style={styles.locationText}>
              📍 현재 위치: {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}
            </Text>
          </View>
        )}

        {route && route.length > 0 && (
          <View style={styles.routeInfo}>
            <Text style={styles.routeText}>
              🛤️ 경로 포인트: {route.length}개
            </Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f0f0f0',
  },
  placeholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8f8f8',
    borderWidth: 2,
    borderColor: '#ddd',
    borderStyle: 'dashed',
    borderRadius: 8,
    margin: 10,
    padding: 20,
  },
  placeholderTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#666',
    marginBottom: 10,
  },
  placeholderText: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    lineHeight: 20,
  },
  locationInfo: {
    position: 'absolute',
    top: 10,
    left: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    padding: 8,
    borderRadius: 6,
  },
  locationText: {
    fontSize: 12,
    color: '#333',
  },
  routeInfo: {
    position: 'absolute',
    top: 10,
    right: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    padding: 8,
    borderRadius: 6,
  },
  routeText: {
    fontSize: 12,
    color: '#333',
  },
});
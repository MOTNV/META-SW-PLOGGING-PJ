import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MapPin } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';

interface WebMapViewProps {
  currentLocation: {
    latitude: number;
    longitude: number;
  } | null;
  routeCoordinates: Array<{
    latitude: number;
    longitude: number;
  }>;
  hasLocationPermission: boolean;
  locationError: string | null;
}

export default function WebMapView({ 
  currentLocation, 
  routeCoordinates, 
  hasLocationPermission, 
  locationError 
}: WebMapViewProps) {
  if (!hasLocationPermission || locationError || !currentLocation) {
    return (
      <LinearGradient
        colors={['#E5E7EB', '#F3F4F6']}
        style={styles.mapPlaceholder}
      >
        <MapPin size={48} color="#9CA3AF" />
        <Text style={styles.mapText}>
          {locationError || (hasLocationPermission ? 'GPS 연결 중...' : '위치 권한 필요')}
        </Text>
        <Text style={styles.mapSubtext}>
          {locationError ? '설정에서 위치 권한을 허용해주세요' : '운동을 시작하면 경로를 추적합니다'}
        </Text>
      </LinearGradient>
    );
  }

  // 웹에서는 간단한 지도 표시 (실제 구현시에는 Google Maps API 등을 사용)
  return (
    <View style={styles.webMapContainer}>
      <LinearGradient
        colors={['#10B981', '#059669']}
        style={styles.webMap}
      >
        <MapPin size={32} color="#ffffff" />
        <Text style={styles.webMapText}>실시간 위치 추적 중</Text>
        <Text style={styles.webMapCoords}>
          위도: {currentLocation.latitude.toFixed(6)}
        </Text>
        <Text style={styles.webMapCoords}>
          경도: {currentLocation.longitude.toFixed(6)}
        </Text>
        {routeCoordinates.length > 0 && (
          <Text style={styles.webMapRoute}>
            경로 포인트: {routeCoordinates.length}개
          </Text>
        )}
      </LinearGradient>
    </View>
  );
}

const styles = StyleSheet.create({
  mapPlaceholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  mapText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#6B7280',
  },
  mapSubtext: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
  },
  webMapContainer: {
    flex: 1,
  },
  webMap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  webMapText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#ffffff',
    marginTop: 12,
  },
  webMapCoords: {
    fontSize: 14,
    color: '#ffffff',
    opacity: 0.9,
  },
  webMapRoute: {
    fontSize: 14,
    color: '#ffffff',
    opacity: 0.8,
    marginTop: 8,
  },
});
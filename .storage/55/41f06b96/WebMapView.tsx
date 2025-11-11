import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { MapPin, RefreshCw } from 'lucide-react-native';
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
  const [webLocationStatus, setWebLocationStatus] = useState<'checking' | 'granted' | 'denied' | 'unavailable'>('checking');
  const [webCurrentLocation, setWebCurrentLocation] = useState<{latitude: number, longitude: number} | null>(null);

  useEffect(() => {
    checkWebLocationPermission();
  }, []);

  const checkWebLocationPermission = async () => {
    if (!navigator.geolocation) {
      setWebLocationStatus('unavailable');
      return;
    }

    try {
      // 웹에서 위치 권한 확인
      const permission = await navigator.permissions.query({ name: 'geolocation' as PermissionName });
      
      if (permission.state === 'granted') {
        setWebLocationStatus('granted');
        getCurrentWebLocation();
      } else if (permission.state === 'denied') {
        setWebLocationStatus('denied');
      } else {
        // 권한이 prompt 상태인 경우 위치 요청
        getCurrentWebLocation();
      }
    } catch (error) {
      console.log('Permission API not supported, trying direct geolocation');
      getCurrentWebLocation();
    }
  };

  const getCurrentWebLocation = () => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setWebLocationStatus('granted');
        setWebCurrentLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        });
      },
      (error) => {
        console.error('Geolocation error:', error);
        if (error.code === error.PERMISSION_DENIED) {
          setWebLocationStatus('denied');
        } else {
          setWebLocationStatus('unavailable');
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000
      }
    );
  };

  const handleRetryLocation = () => {
    setWebLocationStatus('checking');
    checkWebLocationPermission();
  };

  // 웹에서 실제 위치를 사용하거나, 없으면 expo-location에서 받은 위치 사용
  const displayLocation = webCurrentLocation || currentLocation;
  const isLocationAvailable = webLocationStatus === 'granted' && displayLocation;

  if (webLocationStatus === 'checking') {
    return (
      <LinearGradient
        colors={['#E5E7EB', '#F3F4F6']}
        style={styles.mapPlaceholder}
      >
        <RefreshCw size={48} color="#9CA3AF" />
        <Text style={styles.mapText}>위치 권한 확인 중...</Text>
        <Text style={styles.mapSubtext}>잠시만 기다려주세요</Text>
      </LinearGradient>
    );
  }

  if (webLocationStatus === 'denied') {
    return (
      <LinearGradient
        colors={['#FEE2E2', '#FECACA']}
        style={styles.mapPlaceholder}
      >
        <MapPin size={48} color="#EF4444" />
        <Text style={styles.mapErrorText}>위치 권한이 거부되었습니다</Text>
        <Text style={styles.mapSubtext}>
          브라우저 설정에서 위치 권한을 허용해주세요
        </Text>
        <TouchableOpacity style={styles.retryButton} onPress={handleRetryLocation}>
          <Text style={styles.retryButtonText}>다시 시도</Text>
        </TouchableOpacity>
      </LinearGradient>
    );
  }

  if (webLocationStatus === 'unavailable') {
    return (
      <LinearGradient
        colors={['#FEF3C7', '#FDE68A']}
        style={styles.mapPlaceholder}
      >
        <MapPin size={48} color="#F59E0B" />
        <Text style={styles.mapErrorText}>위치 서비스를 사용할 수 없습니다</Text>
        <Text style={styles.mapSubtext}>
          HTTPS 연결이 필요하거나 브라우저가 지원하지 않습니다
        </Text>
      </LinearGradient>
    );
  }

  if (!isLocationAvailable) {
    return (
      <LinearGradient
        colors={['#E5E7EB', '#F3F4F6']}
        style={styles.mapPlaceholder}
      >
        <MapPin size={48} color="#9CA3AF" />
        <Text style={styles.mapText}>GPS 연결 중...</Text>
        <Text style={styles.mapSubtext}>위치를 찾고 있습니다</Text>
      </LinearGradient>
    );
  }

  // 위치가 있을 때 지도 표시
  return (
    <View style={styles.webMapContainer}>
      <LinearGradient
        colors={['#10B981', '#059669']}
        style={styles.webMap}
      >
        <MapPin size={32} color="#ffffff" />
        <Text style={styles.webMapText}>실시간 위치 추적 중</Text>
        <Text style={styles.webMapCoords}>
          위도: {displayLocation.latitude.toFixed(6)}
        </Text>
        <Text style={styles.webMapCoords}>
          경도: {displayLocation.longitude.toFixed(6)}
        </Text>
        {routeCoordinates.length > 0 && (
          <Text style={styles.webMapRoute}>
            경로 포인트: {routeCoordinates.length}개
          </Text>
        )}
        <View style={styles.locationStatus}>
          <View style={styles.statusDot} />
          <Text style={styles.statusText}>GPS 연결됨</Text>
        </View>
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
  mapErrorText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#EF4444',
  },
  mapSubtext: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
    paddingHorizontal: 20,
  },
  retryButton: {
    marginTop: 16,
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#EF4444',
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#ffffff',
    fontWeight: '600',
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
  locationStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 16,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#34D399',
  },
  statusText: {
    fontSize: 12,
    color: '#ffffff',
    opacity: 0.9,
  },
});
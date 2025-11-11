import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { MapPin, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react-native';
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
  const [webLocationStatus, setWebLocationStatus] = useState<'checking' | 'granted' | 'denied' | 'unavailable' | 'prompt'>('checking');
  const [webCurrentLocation, setWebCurrentLocation] = useState<{latitude: number, longitude: number} | null>(null);
  const [isSecureContext, setIsSecureContext] = useState(true);
  const [permissionDetails, setPermissionDetails] = useState<string>('');

  useEffect(() => {
    checkWebLocationPermission();
  }, []);

  const checkWebLocationPermission = async () => {
    // HTTPS 연결 확인
    const isSecure = window.location.protocol === 'https:' || window.location.hostname === 'localhost';
    setIsSecureContext(isSecure);

    if (!navigator.geolocation) {
      setWebLocationStatus('unavailable');
      setPermissionDetails('이 브라우저는 위치 서비스를 지원하지 않습니다.');
      return;
    }

    if (!isSecure) {
      setWebLocationStatus('unavailable');
      setPermissionDetails('HTTPS 연결이 필요합니다. 보안 연결에서만 위치 서비스를 사용할 수 있습니다.');
      return;
    }

    try {
      // 권한 API 지원 확인 (크롬에서 지원)
      if ('permissions' in navigator) {
        const permission = await navigator.permissions.query({ name: 'geolocation' as PermissionName });
        
        setPermissionDetails(`권한 상태: ${permission.state}`);
        
        if (permission.state === 'granted') {
          setWebLocationStatus('granted');
          getCurrentWebLocation();
        } else if (permission.state === 'denied') {
          setWebLocationStatus('denied');
          setPermissionDetails('위치 권한이 거부되었습니다. 브라우저 주소창 왼쪽의 자물쇠 아이콘을 클릭하여 위치 권한을 허용해주세요.');
        } else if (permission.state === 'prompt') {
          setWebLocationStatus('prompt');
          setPermissionDetails('위치 권한을 요청합니다. 허용을 클릭해주세요.');
          // 권한 요청
          requestLocationPermission();
        }

        // 권한 상태 변경 감지
        permission.addEventListener('change', () => {
          setPermissionDetails(`권한 상태 변경: ${permission.state}`);
          if (permission.state === 'granted') {
            setWebLocationStatus('granted');
            getCurrentWebLocation();
          } else if (permission.state === 'denied') {
            setWebLocationStatus('denied');
          }
        });
      } else {
        // 권한 API를 지원하지 않는 브라우저에서는 직접 위치 요청
        setPermissionDetails('권한 API 미지원, 직접 위치 요청 중...');
        requestLocationPermission();
      }
    } catch (error) {
      console.error('권한 확인 오류:', error);
      setPermissionDetails('권한 확인 중 오류 발생, 직접 위치 요청 시도 중...');
      requestLocationPermission();
    }
  };

  const requestLocationPermission = () => {
    setWebLocationStatus('checking');
    setPermissionDetails('위치 정보를 요청하고 있습니다...');

    const options = {
      enableHighAccuracy: true,
      timeout: 15000, // 15초로 타임아웃 증가
      maximumAge: 300000 // 5분
    };

    navigator.geolocation.getCurrentPosition(
      (position) => {
        console.log('위치 획득 성공:', position);
        setWebLocationStatus('granted');
        setWebCurrentLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        });
        setPermissionDetails(`위치 획득 성공 (정확도: ${Math.round(position.coords.accuracy)}m)`);
        
        // 지속적인 위치 추적 시작
        startWatchingPosition();
      },
      (error) => {
        console.error('위치 획득 실패:', error);
        let errorMessage = '';
        
        switch (error.code) {
          case error.PERMISSION_DENIED:
            setWebLocationStatus('denied');
            errorMessage = '위치 권한이 거부되었습니다. 크롬에서는:\n1. 주소창 왼쪽의 자물쇠/위치 아이콘 클릭\n2. "위치" 설정을 "허용"으로 변경\n3. 페이지 새로고침';
            break;
          case error.POSITION_UNAVAILABLE:
            setWebLocationStatus('unavailable');
            errorMessage = '위치 정보를 사용할 수 없습니다. GPS가 비활성화되었거나 실내에 있을 수 있습니다.';
            break;
          case error.TIMEOUT:
            setWebLocationStatus('unavailable');
            errorMessage = '위치 요청 시간이 초과되었습니다. 네트워크 연결을 확인하고 다시 시도해주세요.';
            break;
          default:
            setWebLocationStatus('unavailable');
            errorMessage = '위치 서비스 오류가 발생했습니다.';
            break;
        }
        
        setPermissionDetails(errorMessage);
      },
      options
    );
  };

  const startWatchingPosition = () => {
    const options = {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 5000
    };

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        setWebCurrentLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        });
        setPermissionDetails(`실시간 추적 중 (정확도: ${Math.round(position.coords.accuracy)}m)`);
      },
      (error) => {
        console.warn('위치 추적 오류:', error);
        // 추적 오류는 심각하지 않으므로 상태는 유지
      },
      options
    );

    // 컴포넌트 언마운트 시 정리를 위해 watchId 저장
    return () => {
      navigator.geolocation.clearWatch(watchId);
    };
  };

  const handleRetryLocation = () => {
    setWebLocationStatus('checking');
    setPermissionDetails('다시 시도 중...');
    checkWebLocationPermission();
  };

  const handleOpenSettings = () => {
    alert('크롬에서 위치 권한 허용하기:\n\n1. 주소창 왼쪽의 자물쇠 또는 위치 아이콘을 클릭하세요\n2. "위치" 항목을 "허용"으로 변경하세요\n3. 페이지를 새로고침하세요\n\n또는 크롬 설정 > 개인정보 및 보안 > 사이트 설정 > 위치에서 이 사이트를 허용 목록에 추가하세요.');
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
        <Text style={styles.mapSubtext}>{permissionDetails}</Text>
      </LinearGradient>
    );
  }

  if (webLocationStatus === 'prompt') {
    return (
      <LinearGradient
        colors={['#FEF3C7', '#FDE68A']}
        style={styles.mapPlaceholder}
      >
        <AlertCircle size={48} color="#F59E0B" />
        <Text style={styles.mapText}>위치 권한 요청 중</Text>
        <Text style={styles.mapSubtext}>브라우저에서 위치 권한 허용을 클릭해주세요</Text>
        <Text style={styles.detailText}>{permissionDetails}</Text>
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
        <Text style={styles.mapSubtext}>{permissionDetails}</Text>
        <View style={styles.buttonContainer}>
          <TouchableOpacity style={styles.settingsButton} onPress={handleOpenSettings}>
            <Text style={styles.settingsButtonText}>설정 방법 보기</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.retryButton} onPress={handleRetryLocation}>
            <Text style={styles.retryButtonText}>다시 시도</Text>
          </TouchableOpacity>
        </View>
      </LinearGradient>
    );
  }

  if (webLocationStatus === 'unavailable') {
    return (
      <LinearGradient
        colors={['#FEF3C7', '#FDE68A']}
        style={styles.mapPlaceholder}
      >
        <AlertCircle size={48} color="#F59E0B" />
        <Text style={styles.mapErrorText}>위치 서비스를 사용할 수 없습니다</Text>
        <Text style={styles.mapSubtext}>{permissionDetails}</Text>
        {!isSecureContext && (
          <Text style={styles.httpsWarning}>
            HTTPS 연결이 필요합니다. 보안 연결에서 다시 시도해주세요.
          </Text>
        )}
        <TouchableOpacity style={styles.retryButton} onPress={handleRetryLocation}>
          <Text style={styles.retryButtonText}>다시 시도</Text>
        </TouchableOpacity>
      </LinearGradient>
    );
  }

  if (!isLocationAvailable) {
    return (
      <LinearGradient
        colors={['#E5E7EB', '#F3F4F6']}
        style={styles.mapPlaceholder}
      >
        <RefreshCw size={48} color="#9CA3AF" />
        <Text style={styles.mapText}>GPS 연결 중...</Text>
        <Text style={styles.mapSubtext}>위치를 찾고 있습니다</Text>
        <Text style={styles.detailText}>{permissionDetails}</Text>
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
        <CheckCircle size={32} color="#ffffff" />
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
        <Text style={styles.detailText}>{permissionDetails}</Text>
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
    padding: 20,
  },
  mapText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#6B7280',
    textAlign: 'center',
  },
  mapErrorText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#EF4444',
    textAlign: 'center',
  },
  mapSubtext: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
    paddingHorizontal: 20,
    lineHeight: 20,
  },
  detailText: {
    fontSize: 12,
    color: '#9CA3AF',
    textAlign: 'center',
    paddingHorizontal: 20,
    marginTop: 8,
    lineHeight: 16,
  },
  httpsWarning: {
    fontSize: 12,
    color: '#F59E0B',
    textAlign: 'center',
    paddingHorizontal: 20,
    marginTop: 8,
    fontWeight: '500',
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#EF4444',
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#ffffff',
    fontWeight: '600',
    fontSize: 14,
  },
  settingsButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#6B7280',
    borderRadius: 8,
  },
  settingsButtonText: {
    color: '#ffffff',
    fontWeight: '600',
    fontSize: 14,
  },
  webMapContainer: {
    flex: 1,
  },
  webMap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 20,
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
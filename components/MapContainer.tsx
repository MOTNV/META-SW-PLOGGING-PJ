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

// 카카오맵 타입 정의
declare global {
  interface Window {
    kakao: any;
  }
}

export default function MapContainer({ 
  location, 
  route, 
  onMapReady, 
  style 
}: MapContainerProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const polylineRef = useRef<any>(null);
  const isInitialCenterSet = useRef<boolean>(false);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  // 카카오맵 스크립트 로드
  useEffect(() => {
    if (Platform.OS !== 'web') {
      return;
    }

    const apiKey = process.env.EXPO_PUBLIC_KAKAO_MAP_API_KEY;
    
    if (!apiKey) {
      setMapError('카카오맵 API 키가 설정되지 않았습니다.');
      return;
    }

    // 이미 스크립트가 로드되어 있는지 확인
    if (window.kakao && window.kakao.maps) {
      initializeMap();
      return;
    }

    // 카카오맵 스크립트 동적 로드
    const script = document.createElement('script');
    script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${apiKey}&autoload=false`;
    script.async = true;
    script.onload = () => {
      if (window.kakao && window.kakao.maps) {
        window.kakao.maps.load(() => {
          initializeMap();
        });
      } else {
        setMapError('카카오맵 API를 로드할 수 없습니다.');
      }
    };
    script.onerror = () => {
      setMapError('카카오맵 API 스크립트를 로드하는데 실패했습니다.');
    };
    document.head.appendChild(script);

    return () => {
      // cleanup
      if (markerRef.current) {
        markerRef.current.setMap(null);
      }
      if (polylineRef.current) {
        polylineRef.current.setMap(null);
      }
    };
  }, []);

  // 맵 초기화
  const initializeMap = () => {
    if (!mapContainerRef.current || !window.kakao || !window.kakao.maps) {
      return;
    }

    try {
      // 기본 위치: 서울시청 (위치 정보가 없을 때)
      const defaultPosition = new window.kakao.maps.LatLng(37.5665, 126.9780);
      
      // GPS 좌표를 그대로 사용 (카카오맵이 자동으로 처리)
      let centerPosition = defaultPosition;
      if (location) {
        centerPosition = new window.kakao.maps.LatLng(location.latitude, location.longitude);
      }
      
      // 맵 옵션
      const mapOption = {
        center: centerPosition,
        level: 3, // 확대 레벨 (1-14)
        draggable: true, // 드래그 가능
        scrollwheel: true, // 마우스 휠로 확대/축소 가능
        disableDoubleClick: false, // 더블클릭 확대 가능
        disableDoubleClickZoom: false, // 더블클릭 확대 가능
      };

      // 맵 생성
      const map = new window.kakao.maps.Map(mapContainerRef.current, mapOption);
      mapRef.current = map;

      // React Native의 터치 이벤트가 맵 드래그를 방해하지 않도록
      // 카카오맵 컨테이너에 직접 스타일 적용
      if (mapContainerRef.current) {
        const mapElement = mapContainerRef.current.querySelector('div[style*="position"]') || mapContainerRef.current;
        if (mapElement && mapElement instanceof HTMLElement) {
          mapElement.style.touchAction = 'pan-x pan-y pinch-zoom';
          mapElement.style.pointerEvents = 'auto';
        }
      }

      // 카카오맵이 렌더링된 후 터치 이벤트 처리
      setTimeout(() => {
        // 카카오맵의 모든 자식 요소에 터치 이벤트가 전달되도록
        if (mapContainerRef.current) {
          const allMapElements = mapContainerRef.current.querySelectorAll('*');
          allMapElements.forEach((el) => {
            if (el instanceof HTMLElement) {
              el.style.touchAction = 'pan-x pan-y pinch-zoom';
            }
          });
        }
      }, 100);

      // 현재 위치 마커 추가
      if (location) {
        updateMarker(location);
        // 초기 위치 설정 표시
        isInitialCenterSet.current = true;
      }

      // 경로 폴리라인 추가
      if (route && route.length > 0) {
        updatePolyline(route);
      }

      setMapReady(true);
      onMapReady?.();
    } catch (error) {
      console.error('카카오맵 초기화 오류:', error);
      setMapError('맵을 초기화하는데 실패했습니다.');
    }
  };


  // 마커 업데이트
  const updateMarker = (loc: { latitude: number; longitude: number }) => {
    if (!mapRef.current || !window.kakao || !window.kakao.maps) {
      return;
    }

    try {
      // 기존 마커 제거
      if (markerRef.current) {
        markerRef.current.setMap(null);
      }

      // GPS 좌표를 그대로 사용 (카카오맵이 자동으로 처리)
      const position = new window.kakao.maps.LatLng(loc.latitude, loc.longitude);
      
      // 새 마커 생성
      const marker = new window.kakao.maps.Marker({
        position: position,
        map: mapRef.current
      });

      markerRef.current = marker;

      // 맵 중심은 처음 위치가 설정될 때만 이동
      // 이후에는 사용자가 드래그한 위치를 유지 (자동으로 중심 이동하지 않음)
      if (!isInitialCenterSet.current && location) {
        mapRef.current.setCenter(position);
        isInitialCenterSet.current = true;
      }
    } catch (error) {
      console.error('마커 업데이트 오류:', error);
    }
  };

  // 폴리라인 업데이트 (경로 표시)
  const updatePolyline = (routePoints: Array<{ latitude: number; longitude: number }>) => {
    if (!mapRef.current || !window.kakao || !window.kakao.maps || routePoints.length < 2) {
      return;
    }

    try {
      // 기존 폴리라인 제거
      if (polylineRef.current) {
        polylineRef.current.setMap(null);
      }

      // GPS 좌표를 그대로 사용하여 경로 생성
      const path = routePoints.map(point => 
        new window.kakao.maps.LatLng(point.latitude, point.longitude)
      );

      // 폴리라인 생성
      const polyline = new window.kakao.maps.Polyline({
        path: path,
        strokeWeight: 5,
        strokeColor: '#FF6B6B',
        strokeOpacity: 0.8,
        strokeStyle: 'solid'
      });

      polyline.setMap(mapRef.current);
      polylineRef.current = polyline;

      // 경로가 포함되도록 맵 범위 조정
      if (routePoints.length > 0) {
        const bounds = new window.kakao.maps.LatLngBounds();
        routePoints.forEach(point => {
          bounds.extend(new window.kakao.maps.LatLng(point.latitude, point.longitude));
        });
        mapRef.current.setBounds(bounds);
      }
    } catch (error) {
      console.error('폴리라인 업데이트 오류:', error);
    }
  };

  // 위치 변경 시 마커 업데이트
  useEffect(() => {
    if (mapReady && location && mapRef.current) {
      updateMarker(location);
    }
  }, [location, mapReady]);

  // 경로 변경 시 폴리라인 업데이트
  useEffect(() => {
    if (mapReady && route && route.length > 0 && mapRef.current) {
      updatePolyline(route);
    }
  }, [route, mapReady]);

  // 웹 환경: 카카오맵 렌더링
  if (Platform.OS === 'web') {
    return (
      <div 
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '100%',
          position: 'relative',
          touchAction: 'pan-x pan-y pinch-zoom',
          WebkitTouchCallout: 'none',
          WebkitUserSelect: 'none',
          userSelect: 'none',
          ...style
        }}
      >
        {mapError && (
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: '#f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            zIndex: 1000,
            padding: '20px',
            pointerEvents: 'auto'
          }}>
            <div style={{
              textAlign: 'center',
              color: '#dc2626',
              fontSize: '14px',
              marginBottom: '10px'
            }}>
              ⚠️ {mapError}
            </div>
            {location && (
              <div style={{
                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                color: '#333',
                marginTop: '10px'
              }}>
                📍 현재 위치: {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}
              </div>
            )}
          </div>
        )}
        {!mapReady && !mapError && (
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: '#f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            pointerEvents: 'none'
          }}>
            <div style={{
              textAlign: 'center',
              color: '#666',
              fontSize: '14px'
            }}>
              🗺️ 카카오맵 로딩 중...
            </div>
          </div>
        )}
        {location && mapReady && (
          <div style={{
            position: 'absolute',
            top: '10px',
            left: '10px',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#333',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            zIndex: 1000,
            fontWeight: '500',
            pointerEvents: 'none' // 터치 이벤트가 맵으로 전달되도록
          }}>
            📍 현재 위치
          </div>
        )}
        {route && route.length > 0 && mapReady && (
          <div style={{
            position: 'absolute',
            top: '10px',
            right: '10px',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#333',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            zIndex: 1000,
            fontWeight: '500',
            pointerEvents: 'none' // 터치 이벤트가 맵으로 전달되도록
          }}>
            🛤️ 경로 포인트: {route.length}개
          </div>
        )}
      </div>
    );
  }

  // 네이티브 앱: 기본 뷰 반환
  return (
    <View style={[styles.container, style]}>
      <View style={styles.placeholder}>
        <Text style={styles.placeholderTitle}>🗺️ 맵 영역</Text>
        <Text style={styles.placeholderText}>
          네이티브 앱에서는 React Native Maps 또는{'\n'}
          카카오맵 네이티브 SDK를 사용하세요
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

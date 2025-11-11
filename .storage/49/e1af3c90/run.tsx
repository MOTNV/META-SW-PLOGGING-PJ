import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Dimensions, Alert, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Play, Pause, Square, MapPin, Clock, Trash2, Zap } from 'lucide-react-native';
import * as Location from 'expo-location';
import WebMapView from '../../components/WebMapView';

// 네이티브 플랫폼에서만 react-native-maps 임포트
let MapView: any = null;
let Marker: any = null;
let Polyline: any = null;

if (Platform.OS !== 'web') {
  try {
    const Maps = require('react-native-maps');
    MapView = Maps.default;
    Marker = Maps.Marker;
    Polyline = Maps.Polyline;
  } catch (error) {
    console.log('react-native-maps not available');
  }
}

const { width } = Dimensions.get('window');

interface LocationCoords {
  latitude: number;
  longitude: number;
  timestamp: number;
}

export default function RunScreen() {
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState('00:00:00');
  const [distance, setDistance] = useState('0.00');
  const [trashCount, setTrashCount] = useState(0);
  const [calories, setCalories] = useState('0');
  
  // GPS 관련 상태
  const [currentLocation, setCurrentLocation] = useState<Location.LocationObject | null>(null);
  const [routeCoordinates, setRouteCoordinates] = useState<LocationCoords[]>([]);
  const [hasLocationPermission, setHasLocationPermission] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  
  // 실시간 통계
  const [currentSpeed, setCurrentSpeed] = useState(0);
  const [averageSpeed, setAverageSpeed] = useState(0);
  const [averagePace, setAveragePace] = useState('0\'00"');
  
  // 타이머 관련
  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const locationSubscription = useRef<Location.LocationSubscription | null>(null);

  // 위치 권한 요청 및 초기 위치 설정
  useEffect(() => {
    requestLocationPermission();
    return () => {
      if (locationSubscription.current) {
        locationSubscription.current.remove();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // 타이머 업데이트
  useEffect(() => {
    if (isRunning && !isPaused) {
      timerRef.current = setInterval(() => {
        const now = Date.now();
        const elapsed = startTime ? now - startTime : 0;
        setElapsedTime(elapsed);
        setDuration(formatTime(elapsed));
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRunning, isPaused, startTime]);

  const requestLocationPermission = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setLocationError('위치 권한이 필요합니다');
        setHasLocationPermission(false);
        return;
      }

      setHasLocationPermission(true);
      setLocationError(null);

      // 현재 위치 가져오기
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
      setCurrentLocation(location);
    } catch (error) {
      console.error('위치 권한 요청 실패:', error);
      setLocationError('위치 서비스를 사용할 수 없습니다');
    }
  };

  const startLocationTracking = async () => {
    if (!hasLocationPermission) {
      Alert.alert('권한 필요', '위치 권한이 필요합니다');
      return;
    }

    try {
      locationSubscription.current = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: 1000, // 1초마다 업데이트
          distanceInterval: 1, // 1미터마다 업데이트
        },
        (location) => {
          setCurrentLocation(location);
          
          if (isRunning && !isPaused) {
            const newCoord: LocationCoords = {
              latitude: location.coords.latitude,
              longitude: location.coords.longitude,
              timestamp: location.timestamp,
            };
            
            setRouteCoordinates(prev => {
              const updated = [...prev, newCoord];
              
              // 거리 계산
              if (updated.length > 1) {
                const totalDistance = calculateTotalDistance(updated);
                setDistance(totalDistance.toFixed(2));
                
                // 칼로리 계산 (대략적인 계산: 1km당 60칼로리)
                const estimatedCalories = Math.round(totalDistance * 60);
                setCalories(estimatedCalories.toString());
              }
              
              return updated;
            });
            
            // 현재 속도 업데이트 (m/s를 km/h로 변환)
            if (location.coords.speed) {
              const speedKmh = location.coords.speed * 3.6;
              setCurrentSpeed(speedKmh);
              
              // 평균 속도 계산
              if (elapsedTime > 0) {
                const totalDistanceKm = parseFloat(distance);
                const elapsedHours = elapsedTime / (1000 * 60 * 60);
                const avgSpeed = totalDistanceKm / elapsedHours;
                setAverageSpeed(avgSpeed);
                
                // 평균 페이스 계산 (분/km)
                if (avgSpeed > 0) {
                  const paceMinutes = 60 / avgSpeed;
                  const minutes = Math.floor(paceMinutes);
                  const seconds = Math.round((paceMinutes - minutes) * 60);
                  setAveragePace(`${minutes}'${seconds.toString().padStart(2, '0')}"`);
                }
              }
            }
          }
        }
      );
    } catch (error) {
      console.error('위치 추적 시작 실패:', error);
      Alert.alert('오류', '위치 추적을 시작할 수 없습니다');
    }
  };

  const stopLocationTracking = () => {
    if (locationSubscription.current) {
      locationSubscription.current.remove();
      locationSubscription.current = null;
    }
  };

  const calculateTotalDistance = (coordinates: LocationCoords[]): number => {
    if (coordinates.length < 2) return 0;
    
    let totalDistance = 0;
    for (let i = 1; i < coordinates.length; i++) {
      const prev = coordinates[i - 1];
      const curr = coordinates[i];
      totalDistance += calculateDistance(prev, curr);
    }
    return totalDistance;
  };

  const calculateDistance = (coord1: LocationCoords, coord2: LocationCoords): number => {
    const R = 6371; // 지구 반지름 (km)
    const dLat = toRad(coord2.latitude - coord1.latitude);
    const dLon = toRad(coord2.longitude - coord1.longitude);
    const lat1 = toRad(coord1.latitude);
    const lat2 = toRad(coord2.latitude);

    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.sin(dLon / 2) * Math.sin(dLon / 2) * Math.cos(lat1) * Math.cos(lat2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  };

  const toRad = (value: number): number => {
    return value * Math.PI / 180;
  };

  const formatTime = (milliseconds: number): string => {
    const totalSeconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleStart = async () => {
    setIsRunning(true);
    setIsPaused(false);
    setStartTime(Date.now());
    setRouteCoordinates([]);
    setDistance('0.00');
    setCalories('0');
    setTrashCount(0);
    await startLocationTracking();
  };

  const handlePause = () => {
    setIsPaused(!isPaused);
  };

  const handleStop = () => {
    setIsRunning(false);
    setIsPaused(false);
    setStartTime(null);
    setElapsedTime(0);
    stopLocationTracking();
    
    // 운동 완료 알림
    if (parseFloat(distance) > 0) {
      Alert.alert(
        '플로깅 완료!',
        `거리: ${distance}km\n시간: ${duration}\n쓰레기 수집: ${trashCount}개\n칼로리: ${calories}kcal`,
        [{ text: '확인', style: 'default' }]
      );
    }
  };

  const handleTrashCollected = () => {
    setTrashCount(prev => prev + 1);
  };

  const renderMap = () => {
    if (Platform.OS === 'web') {
      return (
        <WebMapView
          currentLocation={currentLocation ? {
            latitude: currentLocation.coords.latitude,
            longitude: currentLocation.coords.longitude,
          } : null}
          routeCoordinates={routeCoordinates.map(coord => ({
            latitude: coord.latitude,
            longitude: coord.longitude,
          }))}
          hasLocationPermission={hasLocationPermission}
          locationError={locationError}
        />
      );
    }

    if (hasLocationPermission && currentLocation && MapView) {
      return (
        <MapView
          style={styles.map}
          initialRegion={{
            latitude: currentLocation.coords.latitude,
            longitude: currentLocation.coords.longitude,
            latitudeDelta: 0.01,
            longitudeDelta: 0.01,
          }}
          region={{
            latitude: currentLocation.coords.latitude,
            longitude: currentLocation.coords.longitude,
            latitudeDelta: 0.01,
            longitudeDelta: 0.01,
          }}
          showsUserLocation={true}
          followsUserLocation={true}
          showsMyLocationButton={true}
        >
          {/* 현재 위치 마커 */}
          <Marker
            coordinate={{
              latitude: currentLocation.coords.latitude,
              longitude: currentLocation.coords.longitude,
            }}
            title="현재 위치"
          />
          
          {/* 경로 표시 */}
          {routeCoordinates.length > 1 && (
            <Polyline
              coordinates={routeCoordinates.map(coord => ({
                latitude: coord.latitude,
                longitude: coord.longitude,
              }))}
              strokeColor="#10B981"
              strokeWidth={4}
            />
          )}
        </MapView>
      );
    }

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
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>플로깅</Text>
        <Text style={styles.headerSubtitle}>
          {isRunning ? (isPaused ? '일시정지' : '진행 중') : '준비'}
        </Text>
      </View>

      {/* Main Stats */}
      <View style={styles.mainStats}>
        {/* Timer */}
        <View style={styles.timerContainer}>
          <Text style={styles.timerLabel}>시간</Text>
          <Text style={styles.timerValue}>{duration}</Text>
        </View>

        {/* Distance & Trash Counter */}
        <View style={styles.statsRow}>
          <View style={styles.statItem}>
            <MapPin size={20} color="#10B981" />
            <Text style={styles.statValue}>{distance}</Text>
            <Text style={styles.statLabel}>거리 (km)</Text>
          </View>
          <View style={styles.statItem}>
            <Trash2 size={20} color="#10B981" />
            <Text style={styles.statValue}>{trashCount}</Text>
            <Text style={styles.statLabel}>쓰레기 수집</Text>
          </View>
          <View style={styles.statItem}>
            <Zap size={20} color="#10B981" />
            <Text style={styles.statValue}>{calories}</Text>
            <Text style={styles.statLabel}>칼로리</Text>
          </View>
        </View>
      </View>

      {/* Map */}
      <View style={styles.mapContainer}>
        {renderMap()}
      </View>

      {/* Trash Collection Button */}
      <View style={styles.trashSection}>
        <TouchableOpacity 
          style={[
            styles.trashButton,
            (!isRunning || isPaused) && styles.trashButtonDisabled
          ]}
          onPress={handleTrashCollected}
          disabled={!isRunning || isPaused}
        >
          <LinearGradient
            colors={(!isRunning || isPaused) ? ['#9CA3AF', '#6B7280'] : ['#34D399', '#10B981']}
            style={styles.trashButtonGradient}
          >
            <Trash2 size={24} color="#ffffff" />
            <Text style={styles.trashButtonText}>쓰레기 수집 +1</Text>
          </LinearGradient>
        </TouchableOpacity>
      </View>

      {/* Control Buttons */}
      <View style={styles.controls}>
        {!isRunning ? (
          <TouchableOpacity style={styles.startButton} onPress={handleStart}>
            <LinearGradient
              colors={['#10B981', '#059669']}
              style={styles.startButtonGradient}
            >
              <Play size={32} color="#ffffff" />
            </LinearGradient>
          </TouchableOpacity>
        ) : (
          <View style={styles.runningControls}>
            <TouchableOpacity 
              style={styles.controlButton}
              onPress={handlePause}
            >
              <View style={styles.controlButtonBackground}>
                {isPaused ? (
                  <Play size={24} color="#10B981" />
                ) : (
                  <Pause size={24} color="#10B981" />
                )}
              </View>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={styles.stopButton}
              onPress={handleStop}
            >
              <View style={styles.stopButtonBackground}>
                <Square size={24} color="#ffffff" />
              </View>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Quick Stats - 이제 실제 데이터 표시 */}
      <View style={styles.quickStats}>
        <View style={styles.quickStatItem}>
          <Text style={styles.quickStatValue}>
            {isRunning ? averageSpeed.toFixed(1) : '0.0'}
          </Text>
          <Text style={styles.quickStatLabel}>평균 속도</Text>
          <Text style={styles.quickStatUnit}>km/h</Text>
        </View>
        <View style={styles.quickStatItem}>
          <Text style={styles.quickStatValue}>
            {isRunning ? averagePace : '0\'00"'}
          </Text>
          <Text style={styles.quickStatLabel}>평균 페이스</Text>
          <Text style={styles.quickStatUnit}>분/km</Text>
        </View>
        <View style={styles.quickStatItem}>
          <Text style={styles.quickStatValue}>
            {isRunning ? Math.round(currentSpeed * 2 + 60) : '0'}
          </Text>
          <Text style={styles.quickStatLabel}>예상 심박</Text>
          <Text style={styles.quickStatUnit}>bpm</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  header: {
    padding: 20,
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '800',
    color: '#1F2937',
  },
  headerSubtitle: {
    fontSize: 16,
    color: '#6B7280',
    marginTop: 4,
    fontWeight: '500',
  },
  mainStats: {
    padding: 20,
    alignItems: 'center',
  },
  timerContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  timerLabel: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  timerValue: {
    fontSize: 48,
    fontWeight: '800',
    color: '#1F2937',
    marginTop: 8,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 32,
  },
  statItem: {
    alignItems: 'center',
    gap: 8,
  },
  statValue: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1F2937',
  },
  statLabel: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  mapContainer: {
    flex: 1,
    margin: 20,
    borderRadius: 12,
    overflow: 'hidden',
  },
  map: {
    flex: 1,
  },
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
  trashSection: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  trashButton: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  trashButtonDisabled: {
    opacity: 0.5,
  },
  trashButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    gap: 12,
  },
  trashButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
  },
  controls: {
    paddingHorizontal: 20,
    alignItems: 'center',
    marginBottom: 20,
  },
  startButton: {
    borderRadius: 40,
    overflow: 'hidden',
  },
  startButtonGradient: {
    width: 80,
    height: 80,
    alignItems: 'center',
    justifyContent: 'center',
  },
  runningControls: {
    flexDirection: 'row',
    gap: 24,
  },
  controlButton: {
    borderRadius: 30,
  },
  controlButtonBackground: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  stopButton: {
    borderRadius: 30,
  },
  stopButtonBackground: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#EF4444',
    alignItems: 'center',
    justifyContent: 'center',
  },
  quickStats: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingBottom: 20,
    gap: 16,
  },
  quickStatItem: {
    flex: 1,
    backgroundColor: '#F9FAFB',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  quickStatValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1F2937',
  },
  quickStatLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
    textAlign: 'center',
  },
  quickStatUnit: {
    fontSize: 10,
    color: '#9CA3AF',
    marginTop: 2,
  },
});
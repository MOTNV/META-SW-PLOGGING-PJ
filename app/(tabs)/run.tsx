import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import MapContainer from '../../components/MapContainer';

interface LocationData {
  latitude: number;
  longitude: number;
  accuracy?: number;
  speed?: number;
  timestamp: string;
}

export default function RunScreen() {
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [distance, setDistance] = useState(0);
  const [currentLocation, setCurrentLocation] = useState<LocationData | null>(null);
  const [route, setRoute] = useState<LocationData[]>([]);
  const [trashCount, setTrashCount] = useState(0);
  const [calories, setCalories] = useState(0);
  const [locationPermission, setLocationPermission] = useState<boolean>(false);
  const [locationError, setLocationError] = useState<string>('');

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const locationWatchRef = useRef<Location.LocationSubscription | null>(null);
  const startTimeRef = useRef<number | null>(null);

  // 위치 권한 요청
  useEffect(() => {
    requestLocationPermission();
    return () => {
      cleanup();
    };
  }, []);

  const cleanup = () => {
    if (locationWatchRef.current) {
      locationWatchRef.current.remove();
      locationWatchRef.current = null;
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const requestLocationPermission = async () => {
    try {
      setLocationError('');
      
      if (Platform.OS === 'web') {
        // 웹에서는 브라우저 geolocation API 사용
        if (!navigator.geolocation) {
          setLocationError('이 브라우저는 위치 서비스를 지원하지 않습니다.');
          return;
        }

        navigator.geolocation.getCurrentPosition(
          (position) => {
            setLocationPermission(true);
            const locationData: LocationData = {
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy || undefined,
              speed: position.coords.speed || undefined,
              timestamp: new Date().toISOString(),
            };
            setCurrentLocation(locationData);
            setLocationError('');
          },
          (error) => {
            console.error('웹 위치 권한 오류:', error);
            setLocationPermission(false);
            switch (error.code) {
              case error.PERMISSION_DENIED:
                setLocationError('위치 권한이 거부되었습니다. 브라우저 설정에서 위치 권한을 허용해주세요.');
                break;
              case error.POSITION_UNAVAILABLE:
                setLocationError('위치 정보를 사용할 수 없습니다.');
                break;
              case error.TIMEOUT:
                setLocationError('위치 요청 시간이 초과되었습니다.');
                break;
              default:
                setLocationError('위치 서비스 오류가 발생했습니다.');
                break;
            }
          },
          {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000
          }
        );
        return;
      }

      // 네이티브에서는 expo-location 사용
      const serviceEnabled = await Location.hasServicesEnabledAsync();
      if (!serviceEnabled) {
        setLocationError('위치 서비스가 비활성화되어 있습니다. 설정에서 위치 서비스를 활성화해주세요.');
        return;
      }

      let { status } = await Location.getForegroundPermissionsAsync();
      
      if (status !== 'granted') {
        const { status: newStatus } = await Location.requestForegroundPermissionsAsync();
        status = newStatus;
      }

      if (status === 'granted') {
        setLocationPermission(true);
        setLocationError('');
        
        try {
          const location = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.High,
            timeInterval: 1000,
            distanceInterval: 1,
          });
          
          const locationData: LocationData = {
            latitude: location.coords.latitude,
            longitude: location.coords.longitude,
            accuracy: location.coords.accuracy || undefined,
            speed: location.coords.speed || undefined,
            timestamp: new Date().toISOString(),
          };
          
          setCurrentLocation(locationData);
        } catch (error) {
          console.error('초기 위치 가져오기 실패:', error);
          setLocationError('현재 위치를 가져올 수 없습니다. GPS 신호를 확인해주세요.');
        }
      } else {
        setLocationPermission(false);
        setLocationError('위치 권한이 필요합니다. 설정에서 위치 권한을 허용해주세요.');
      }
    } catch (error) {
      console.error('위치 권한 요청 실패:', error);
      setLocationError('위치 권한 요청 중 오류가 발생했습니다.');
    }
  };

  // 실시간 위치 추적 시작
  const startLocationTracking = async () => {
    if (!locationPermission) {
      Alert.alert('권한 필요', '위치 권한이 필요합니다.');
      await requestLocationPermission();
      return;
    }

    try {
      if (Platform.OS === 'web') {
        // 웹에서는 watchPosition 사용
        const watchId = navigator.geolocation.watchPosition(
          (position) => {
            const locationData: LocationData = {
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy || undefined,
              speed: position.coords.speed || undefined,
              timestamp: new Date().toISOString(),
            };

            setCurrentLocation(locationData);
            
            if (isRunning && !isPaused) {
              setRoute(prevRoute => {
                const newRoute = [...prevRoute, locationData];
                
                // 거리 계산
                if (prevRoute.length > 0) {
                  const lastLocation = prevRoute[prevRoute.length - 1];
                  const distanceIncrement = calculateDistance(
                    lastLocation.latitude,
                    lastLocation.longitude,
                    locationData.latitude,
                    locationData.longitude
                  );
                  setDistance(prevDistance => prevDistance + distanceIncrement);
                }
                
                return newRoute;
              });
            }
          },
          (error) => {
            console.error('웹 위치 추적 오류:', error);
          },
          {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 1000
          }
        );

        locationWatchRef.current = {
          remove: () => navigator.geolocation.clearWatch(watchId)
        } as any;
        return;
      }

      // 네이티브에서는 expo-location 사용
      locationWatchRef.current = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: 2000,
          distanceInterval: 5,
        },
        (location) => {
          const locationData: LocationData = {
            latitude: location.coords.latitude,
            longitude: location.coords.longitude,
            accuracy: location.coords.accuracy || undefined,
            speed: location.coords.speed || undefined,
            timestamp: new Date().toISOString(),
          };

          setCurrentLocation(locationData);
          
          if (isRunning && !isPaused) {
            setRoute(prevRoute => {
              const newRoute = [...prevRoute, locationData];
              
              if (prevRoute.length > 0) {
                const lastLocation = prevRoute[prevRoute.length - 1];
                const distanceIncrement = calculateDistance(
                  lastLocation.latitude,
                  lastLocation.longitude,
                  locationData.latitude,
                  locationData.longitude
                );
                setDistance(prevDistance => prevDistance + distanceIncrement);
              }
              
              return newRoute;
            });
          }
        }
      );
    } catch (error) {
      console.error('위치 추적 시작 실패:', error);
      setLocationError('위치 추적을 시작할 수 없습니다.');
    }
  };

  // 위치 추적 중지
  const stopLocationTracking = () => {
    if (locationWatchRef.current) {
      locationWatchRef.current.remove();
      locationWatchRef.current = null;
    }
  };

  // 두 지점 간의 거리 계산 (Haversine formula)
  const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 6371; // 지구 반지름 (km)
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
      Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
      Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  };

  // 칼로리 계산
  const calculateCalories = (distanceKm: number, durationMinutes: number): number => {
    const caloriesPerMinute = 10;
    return Math.round(durationMinutes * caloriesPerMinute);
  };

  // 타이머 시작
  const startTimer = () => {
    startTimeRef.current = Date.now();
    timerRef.current = setInterval(() => {
      if (startTimeRef.current) {
        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
        setDuration(elapsed);
        setCalories(calculateCalories(distance, elapsed / 60));
      }
    }, 1000);
  };

  // 타이머 중지
  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  // 운동 시작
  const handleStart = async () => {
    console.log('운동 시작 버튼 클릭됨');
    
    if (!locationPermission) {
      Alert.alert('위치 권한 필요', '플로깅을 시작하려면 위치 권한이 필요합니다.');
      await requestLocationPermission();
      return;
    }

    try {
      setIsRunning(true);
      setIsPaused(false);
      setDuration(0);
      setDistance(0);
      setRoute([]);
      setTrashCount(0);
      setCalories(0);
      
      startTimer();
      await startLocationTracking();
      
      console.log('운동 시작됨');
    } catch (error) {
      console.error('운동 시작 오류:', error);
      Alert.alert('오류', '운동을 시작할 수 없습니다.');
    }
  };

  // 운동 일시정지
  const handlePause = () => {
    console.log('일시정지 버튼 클릭됨');
    setIsPaused(!isPaused);
    if (!isPaused) {
      stopTimer();
    } else {
      startTimer();
    }
  };

  // 운동 종료
  const handleStop = () => {
    console.log('운동 종료 버튼 클릭됨');
    
    Alert.alert(
      '운동 종료',
      '정말로 운동을 종료하시겠습니까?',
      [
        { text: '취소', style: 'cancel' },
        {
          text: '종료',
          style: 'destructive',
          onPress: () => {
            setIsRunning(false);
            setIsPaused(false);
            stopTimer();
            stopLocationTracking();
            startTimeRef.current = null;
            
            Alert.alert(
              '운동 완료!',
              `거리: ${distance.toFixed(2)}km\n시간: ${Math.floor(duration / 60)}분 ${duration % 60}초\n칼로리: ${calories}kcal\n쓰레기: ${trashCount}개`,
              [
                {
                  text: '확인',
                  onPress: () => {
                    // 필요시 여기서 데이터 저장 로직 추가
                  }
                }
              ]
            );
          }
        }
      ]
    );
  };

  // 쓰레기 수집
  const handleTrashCollection = () => {
    setTrashCount(prev => prev + 1);
    Alert.alert('쓰레기 수집!', `총 ${trashCount + 1}개의 쓰레기를 수집했습니다.`);
  };

  // 시간 포맷팅
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <View style={styles.container}>
      {/* 맵 영역 */}
      <View 
        style={styles.mapContainer}
        {...(Platform.OS === 'web' && {
          // 웹에서는 React Native의 터치 이벤트가 맵을 방해하지 않도록
          onStartShouldSetResponder: () => false,
          onMoveShouldSetResponder: () => false,
        })}
      >
        <MapContainer
          location={currentLocation}
          route={route}
          style={styles.map}
          onMapReady={() => console.log('맵이 준비되었습니다')}
        />
        
        {locationError ? (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{locationError}</Text>
            <TouchableOpacity 
              style={styles.retryButton} 
              onPress={requestLocationPermission}
            >
              <Text style={styles.retryButtonText}>다시 시도</Text>
            </TouchableOpacity>
          </View>
        ) : null}
      </View>

      {/* 통계 정보 */}
      <View style={styles.statsContainer}>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{formatTime(duration)}</Text>
          <Text style={styles.statLabel}>시간</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{distance.toFixed(2)}</Text>
          <Text style={styles.statLabel}>거리 (km)</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{calories}</Text>
          <Text style={styles.statLabel}>칼로리</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{trashCount}</Text>
          <Text style={styles.statLabel}>쓰레기</Text>
        </View>
      </View>

      {/* 컨트롤 버튼 */}
      <View style={styles.controlsContainer}>
        {!isRunning ? (
          <TouchableOpacity 
            style={[styles.controlButton, styles.startButton]} 
            onPress={handleStart}
            activeOpacity={0.7}
          >
            <Ionicons name="play" size={32} color="white" />
            <Text style={styles.controlButtonText}>시작</Text>
          </TouchableOpacity>
        ) : (
          <View style={styles.runningControls}>
            <TouchableOpacity 
              style={[styles.controlButton, isPaused ? styles.resumeButton : styles.pauseButton]} 
              onPress={handlePause}
              activeOpacity={0.7}
            >
              <Ionicons name={isPaused ? "play" : "pause"} size={24} color="white" />
              <Text style={styles.controlButtonText}>{isPaused ? "재개" : "일시정지"}</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.controlButton, styles.trashButton]} 
              onPress={handleTrashCollection}
              activeOpacity={0.7}
            >
              <Ionicons name="trash" size={24} color="white" />
              <Text style={styles.controlButtonText}>쓰레기 수집</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.controlButton, styles.stopButton]} 
              onPress={handleStop}
              activeOpacity={0.7}
            >
              <Ionicons name="stop" size={24} color="white" />
              <Text style={styles.controlButtonText}>종료</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* 상태 표시 */}
      <View style={styles.statusContainer}>
        <Text style={styles.statusText}>
          상태: {isRunning ? (isPaused ? '일시정지' : '운동 중') : '대기'}
        </Text>
        <Text style={styles.statusText}>
          GPS: {locationPermission ? '연결됨' : '연결 안됨'}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  mapContainer: {
    flex: 1,
    position: 'relative',
    // 웹에서 터치 이벤트가 맵으로 전달되도록
    ...(Platform.OS === 'web' && {
      touchAction: 'none',
      pointerEvents: 'auto',
    }),
  },
  map: {
    flex: 1,
    // 웹에서 터치 이벤트가 맵으로 전달되도록
    ...(Platform.OS === 'web' && {
      touchAction: 'pan-x pan-y pinch-zoom',
      pointerEvents: 'auto',
    }),
  },
  errorContainer: {
    position: 'absolute',
    top: 20,
    left: 20,
    right: 20,
    backgroundColor: 'rgba(255, 0, 0, 0.9)',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  errorText: {
    color: 'white',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 10,
  },
  retryButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 5,
  },
  retryButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: 'bold',
  },
  statsContainer: {
    flexDirection: 'row',
    backgroundColor: 'white',
    paddingVertical: 20,
    paddingHorizontal: 10,
    justifyContent: 'space-around',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  controlsContainer: {
    backgroundColor: 'white',
    paddingVertical: 20,
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  controlButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 15,
    paddingHorizontal: 20,
    borderRadius: 25,
    marginHorizontal: 5,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
  },
  controlButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  startButton: {
    backgroundColor: '#4CAF50',
    flex: 1,
  },
  runningControls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  pauseButton: {
    backgroundColor: '#FF9800',
    flex: 1,
  },
  resumeButton: {
    backgroundColor: '#4CAF50',
    flex: 1,
  },
  trashButton: {
    backgroundColor: '#2196F3',
    flex: 1,
  },
  stopButton: {
    backgroundColor: '#f44336',
    flex: 1,
  },
  statusContainer: {
    backgroundColor: 'white',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  statusText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    marginVertical: 2,
  },
});
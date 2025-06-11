// Copyright (C) 2025 HockHead Project. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Common/UdpSocketReceiver.h"
#include "UdpReceiverComponent.generated.h"

// Delegate for UDP message received events
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnUdpMessageReceived, const FString&, Message);

/**
 * Component that listens for UDP messages from the Python orchestrator.
 * Receives filenames of audio files to be played by the MetaHuman avatar.
 */
UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class AIAVATAR_API UUdpReceiverComponent : public UActorComponent
{
	GENERATED_BODY()

public:	
	// Sets default values for this component's properties
	UUdpReceiverComponent();

	// Called when the game starts or when spawned
	virtual void BeginPlay() override;
	
	// Called when the game ends or when destroyed
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	// Called every frame
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Event fired when a UDP message is received */
	UPROPERTY(BlueprintAssignable, Category = "Network")
	FOnUdpMessageReceived OnMessageReceived;

	/** Start listening for UDP messages */
	UFUNCTION(BlueprintCallable, Category = "Network")
	bool StartListening();

	/** Stop listening for UDP messages */
	UFUNCTION(BlueprintCallable, Category = "Network")
	void StopListening();

	/** Send a test message to verify the connection */
	UFUNCTION(BlueprintCallable, Category = "Network")
	bool SendTestMessage(const FString& Message);

	/** Check if the receiver is currently listening */
	UFUNCTION(BlueprintPure, Category = "Network")
	bool IsListening() const;

protected:
	/** Port to listen on for UDP messages */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Network", meta = (ClampMin = "0", ClampMax = "65535"))
	int32 UdpPort = 5555;

	/** Whether to automatically start listening when the component begins play */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Network")
	bool bAutoStart = true;

	/** Maximum size of UDP messages to receive (in bytes) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Network", meta = (ClampMin = "256", ClampMax = "65507"))
	int32 MaxReceiveSize = 1024;

private:
	/** Socket used for receiving UDP messages */
	FSocket* ListenSocket;

	/** UDP receiver that handles the socket in a separate thread */
	FUdpSocketReceiver* UdpReceiver;

	/** Callback function for when data is received on the UDP socket */
	void OnUdpReceive(const FArrayReaderPtr& DataPtr, const FIPv4Endpoint& Endpoint);

	/** Internal flag to track if we're currently listening */
	bool bIsListening;
};

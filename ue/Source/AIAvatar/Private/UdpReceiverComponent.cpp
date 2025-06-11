// Copyright (C) 2025 HockHead Project. All Rights Reserved.

#include "UdpReceiverComponent.h"
#include "SocketSubsystem.h"
#include "IPAddress.h"
#include "Interfaces/IPv4/IPv4Endpoint.h"
#include "HAL/RunnableThread.h"

UUdpReceiverComponent::UUdpReceiverComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	ListenSocket = nullptr;
	UdpReceiver = nullptr;
	bIsListening = false;
}

void UUdpReceiverComponent::BeginPlay()
{
	Super::BeginPlay();
	
	if (bAutoStart)
	{
		StartListening();
	}
}

void UUdpReceiverComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopListening();
	Super::EndPlay(EndPlayReason);
}

void UUdpReceiverComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	// UDP receiver runs on its own thread, so no need for tick processing
}

bool UUdpReceiverComponent::StartListening()
{
	// Don't start if already listening
	if (bIsListening)
	{
		UE_LOG(LogTemp, Warning, TEXT("UDP Receiver already listening on port %d"), UdpPort);
		return true;
	}

	// Get socket subsystem
	ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
	if (!SocketSubsystem)
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to get socket subsystem"));
		return false;
	}

	// Create UDP socket
	ListenSocket = SocketSubsystem->CreateSocket(NAME_DGram, TEXT("UDP Receiver Socket"), false);
	if (!ListenSocket)
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to create UDP socket"));
		return false;
	}

	// Allow binding to the same address
	ListenSocket->SetReuseAddr(true);
	
	// Set buffer size
	int32 NewSize = 0;
	ListenSocket->SetReceiveBufferSize(MaxReceiveSize, NewSize);
	
	// Bind to local address and port
	FIPv4Address::Any.Value;
	FIPv4Endpoint Endpoint(FIPv4Address::Any, UdpPort);
	
	if (!ListenSocket->Bind(*Endpoint.ToInternetAddr()))
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to bind socket to port %d"), UdpPort);
		SocketSubsystem->DestroySocket(ListenSocket);
		ListenSocket = nullptr;
		return false;
	}
	
	// Create UDP receiver
	UdpReceiver = new FUdpSocketReceiver(ListenSocket, FTimespan::FromMilliseconds(100), TEXT("UDP Receiver Thread"));
	if (UdpReceiver)
	{
		// Set callback for data received
		UdpReceiver->OnDataReceived().BindUObject(this, &UUdpReceiverComponent::OnUdpReceive);
		
		// Start the receiver thread
		UdpReceiver->Start();
		
		bIsListening = true;
		UE_LOG(LogTemp, Log, TEXT("UDP Receiver listening on port %d"), UdpPort);
		return true;
	}
	
	UE_LOG(LogTemp, Error, TEXT("Failed to create UDP receiver"));
	SocketSubsystem->DestroySocket(ListenSocket);
	ListenSocket = nullptr;
	return false;
}

void UUdpReceiverComponent::StopListening()
{
	if (UdpReceiver)
	{
		UdpReceiver->Stop();
		delete UdpReceiver;
		UdpReceiver = nullptr;
	}
	
	if (ListenSocket)
	{
		ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
		if (SocketSubsystem)
		{
			SocketSubsystem->DestroySocket(ListenSocket);
		}
		ListenSocket = nullptr;
	}
	
	bIsListening = false;
	UE_LOG(LogTemp, Log, TEXT("UDP Receiver stopped"));
}

bool UUdpReceiverComponent::SendTestMessage(const FString& Message)
{
	if (!bIsListening || !ListenSocket)
	{
		UE_LOG(LogTemp, Warning, TEXT("Cannot send test message: UDP Receiver not listening"));
		return false;
	}
	
	ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
	if (!SocketSubsystem)
	{
		return false;
	}
	
	// Create a loopback address to send to ourselves
	TSharedRef<FInternetAddr> DestAddr = SocketSubsystem->CreateInternetAddr();
	bool bIsValid = false;
	DestAddr->SetIp(TEXT("127.0.0.1"), bIsValid);
	if (!bIsValid)
	{
		return false;
	}
	DestAddr->SetPort(UdpPort);
	
	// Convert string to UTF-8 bytes
	FTCHARToUTF8 Converter(*Message);
	int32 BytesSent = 0;
	
	// Send the message
	return ListenSocket->SendTo(
		(const uint8*)Converter.Get(), 
		Converter.Length(), 
		BytesSent, 
		*DestAddr
	) && BytesSent > 0;
}

bool UUdpReceiverComponent::IsListening() const
{
	return bIsListening;
}

void UUdpReceiverComponent::OnUdpReceive(const FArrayReaderPtr& DataPtr, const FIPv4Endpoint& Endpoint)
{
	if (!DataPtr.IsValid() || DataPtr->Num() <= 0)
	{
		return;
	}
	
	// Ensure the data is null-terminated
	const uint8* Data = DataPtr->GetData();
	int32 DataSize = DataPtr->Num();
	
	// Convert received bytes to UTF-8 string
	FString ReceivedMessage;
	
	// Create a buffer with null terminator
	TArray<ANSICHAR> AnsiBuffer;
	AnsiBuffer.SetNum(DataSize + 1);
	FMemory::Memcpy(AnsiBuffer.GetData(), Data, DataSize);
	AnsiBuffer[DataSize] = 0; // Null terminator
	
	// Convert ANSI to FString
	ReceivedMessage = FString(UTF8_TO_TCHAR(AnsiBuffer.GetData()));
	
	UE_LOG(LogTemp, Log, TEXT("UDP Message Received: %s from %s"), *ReceivedMessage, *Endpoint.ToString());
	
	// Broadcast the message via delegate (on game thread)
	AsyncTask(ENamedThreads::GameThread, [this, ReceivedMessage]() {
		OnMessageReceived.Broadcast(ReceivedMessage);
	});
}

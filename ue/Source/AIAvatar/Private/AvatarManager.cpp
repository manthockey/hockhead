// Copyright (C) 2025 HockHead Project. All Rights Reserved.

#include "AvatarManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

AAvatarManager::AAvatarManager()
{
	PrimaryActorTick.bCanEverTick = true;

	// Create components
	UdpReceiver = CreateDefaultSubobject<UUdpReceiverComponent>(TEXT("UdpReceiver"));
	AudioComponent = CreateDefaultSubobject<UAudioComponent>(TEXT("AudioComponent"));
	
	// Set default values
	AudioDirectory = FPaths::ProjectContentDir() + TEXT("Audio");
	bIsAudioPlaying = false;
	CurrentSoundWave = nullptr;
	AudioImporter = nullptr;
}

void AAvatarManager::BeginPlay()
{
	Super::BeginPlay();
	
	// Ensure audio directory exists
	IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
	if (!PlatformFile.DirectoryExists(*AudioDirectory))
	{
		PlatformFile.CreateDirectory(*AudioDirectory);
	}
	
	// Bind UDP message received delegate
	if (UdpReceiver)
	{
		UdpReceiver->OnMessageReceived.AddDynamic(this, &AAvatarManager::OnUdpMessageReceived);
		
		if (bAutoStartListener)
		{
			StartListener();
		}
	}
	
	// Initialize audio component
	if (AudioComponent)
	{
		AudioComponent->bAutoActivate = false;
		AudioComponent->bAlwaysPlay = true;
	}
	
	// Log initialization
	UE_LOG(LogTemp, Log, TEXT("AvatarManager initialized. Audio directory: %s"), *AudioDirectory);
}

void AAvatarManager::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	
	// Nothing to do in tick for now
	// Future: Could monitor audio playback state or add idle animations
}

void AAvatarManager::StartListener()
{
	if (UdpReceiver && !UdpReceiver->IsListening())
	{
		if (UdpReceiver->StartListening())
		{
			UE_LOG(LogTemp, Log, TEXT("UDP listener started"));
		}
		else
		{
			UE_LOG(LogTemp, Error, TEXT("Failed to start UDP listener"));
		}
	}
}

void AAvatarManager::StopListener()
{
	if (UdpReceiver && UdpReceiver->IsListening())
	{
		UdpReceiver->StopListening();
		UE_LOG(LogTemp, Log, TEXT("UDP listener stopped"));
	}
}

void AAvatarManager::OnUdpMessageReceived(const FString& Message)
{
	// Log the received message
	UE_LOG(LogTemp, Log, TEXT("UDP message received: %s"), *Message);
	
	// Handle test connection message
	if (Message == TEXT("TEST_CONNECTION"))
	{
		UE_LOG(LogTemp, Log, TEXT("Received test connection message"));
		return;
	}
	
	// Build the full file path
	FString FilePath = GetFullAudioPath(Message);
	
	// Check if file exists
	if (FPaths::FileExists(FilePath))
	{
		UE_LOG(LogTemp, Log, TEXT("Audio file found: %s"), *FilePath);
		
		// Stop any currently playing audio
		StopCurrentAudio();
		
		// Import and play the new audio
		ImportAndPlayAudio(FilePath);
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Audio file not found: %s"), *FilePath);
	}
}

FString AAvatarManager::GetFullAudioPath(const FString& Filename)
{
	// If the filename already has a path, use it as is
	if (Filename.Contains(TEXT("/")))
	{
		return Filename;
	}
	
	// Otherwise, combine with the audio directory
	return FPaths::Combine(AudioDirectory, Filename);
}

void AAvatarManager::ImportAndPlayAudio(const FString& FilePath)
{
	// Create audio importer if it doesn't exist
	if (!AudioImporter)
	{
		AudioImporter = URuntimeAudioImporterLibrary::CreateRuntimeAudioImporter();
	}
	
	if (AudioImporter)
	{
		// Bind the completion callback
		AudioImporter->OnResultNative.AddUObject(this, &AAvatarManager::OnAudioImportComplete);
		
		// Start async import
		AudioImporter->ImportAudioFromFile(FilePath, ERuntimeAudioFormat::Auto);
		
		UE_LOG(LogTemp, Log, TEXT("Started importing audio file: %s"), *FilePath);
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to create audio importer"));
	}
}

void AAvatarManager::OnAudioImportComplete(URuntimeAudioImporterLibrary* Importer, UImportedSoundWave* ImportedSoundWave, ERuntimeImportStatus Status)
{
	// Check if import was successful
	if (Status == ERuntimeImportStatus::SuccessfulImport && ImportedSoundWave)
	{
		UE_LOG(LogTemp, Log, TEXT("Audio import successful"));
		
		// Store the current sound wave
		CurrentSoundWave = ImportedSoundWave;
		
		// Set and play the sound
		if (AudioComponent)
		{
			AudioComponent->SetSound(ImportedSoundWave);
			AudioComponent->Play();
			bIsAudioPlaying = true;
			
			UE_LOG(LogTemp, Log, TEXT("Started audio playback"));
			
			// Start lip sync
			StartLipSync(ImportedSoundWave);
		}
		else
		{
			UE_LOG(LogTemp, Error, TEXT("AudioComponent is null"));
		}
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Audio import failed with status: %d"), (int32)Status);
	}
}

void AAvatarManager::StartLipSync(UImportedSoundWave* SoundWave)
{
	// Check if we have the necessary components for lip sync
	if (LipSyncComponent && FaceMesh && SoundWave)
	{
		// Start lip sync with the imported sound wave
		LipSyncComponent->PlayLipSync(SoundWave);
		
		UE_LOG(LogTemp, Log, TEXT("Started lip sync for current audio"));
	}
	else
	{
		if (!LipSyncComponent)
		{
			UE_LOG(LogTemp, Warning, TEXT("LipSyncComponent not set - lip sync disabled"));
		}
		
		if (!FaceMesh)
		{
			UE_LOG(LogTemp, Warning, TEXT("FaceMesh not set - lip sync disabled"));
		}
	}
}

void AAvatarManager::StopCurrentAudio()
{
	if (bIsAudioPlaying && AudioComponent)
	{
		// Stop audio playback
		AudioComponent->Stop();
		bIsAudioPlaying = false;
		
		// Stop lip sync if component exists
		if (LipSyncComponent)
		{
			LipSyncComponent->StopLipSync();
		}
		
		UE_LOG(LogTemp, Log, TEXT("Stopped current audio and lip sync"));
	}
}

void AAvatarManager::TestAudioPlayback(const FString& TestAudioPath)
{
	FString FilePath = TestAudioPath;
	
	// If no path provided, try to find a test file in the audio directory
	if (TestAudioPath.IsEmpty())
	{
		TArray<FString> FoundFiles;
		IFileManager::Get().FindFiles(FoundFiles, *(AudioDirectory / TEXT("*.mp3")), true, false);
		
		if (FoundFiles.Num() > 0)
		{
			FilePath = AudioDirectory / FoundFiles[0];
		}
		else
		{
			UE_LOG(LogTemp, Error, TEXT("No test audio files found in %s"), *AudioDirectory);
			return;
		}
	}
	
	// Check if file exists
	if (FPaths::FileExists(FilePath))
	{
		UE_LOG(LogTemp, Log, TEXT("Testing audio playback with file: %s"), *FilePath);
		
		// Stop any current playback
		StopCurrentAudio();
		
		// Import and play the test audio
		ImportAndPlayAudio(FilePath);
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Test audio file not found: %s"), *FilePath);
	}
}

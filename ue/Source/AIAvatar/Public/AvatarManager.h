// Copyright (C) 2025 HockHead Project. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Components/AudioComponent.h"
#include "UdpReceiverComponent.h"
#include "RuntimeAudioImporterLibrary.h"
#include "RuntimeAudioImporterTypes.h"
#include "MetaHumanRuntimeLipSync.h"
#include "AvatarManager.generated.h"

/**
 * Main actor that manages the AI Avatar system in Unreal Engine.
 * Handles UDP messages from Python orchestrator, loads audio files,
 * plays them through an AudioComponent, and drives MetaHuman lip sync.
 */
UCLASS()
class AIAVATAR_API AAvatarManager : public AActor
{
	GENERATED_BODY()
	
public:	
	// Sets default values for this actor's properties
	AAvatarManager();

	// Called when the game starts or when spawned
	virtual void BeginPlay() override;
	
	// Called every frame
	virtual void Tick(float DeltaTime) override;

	/** UDP Receiver component for listening to messages from Python orchestrator */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	UUdpReceiverComponent* UdpReceiver;

	/** Audio component for playing TTS audio */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	UAudioComponent* AudioComponent;
	
	/** Path to the directory where audio files are stored */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	FString AudioDirectory;
	
	/** Whether to automatically start the UDP listener on BeginPlay */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Network")
	bool bAutoStartListener = true;
	
	/** Reference to the MetaHuman face mesh for lip sync */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LipSync")
	USkeletalMeshComponent* FaceMesh;
	
	/** Reference to the Runtime Lip Sync component */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "LipSync")
	UMetaHumanRuntimeLipSyncComponent* LipSyncComponent;
	
	/** Start listening for UDP messages */
	UFUNCTION(BlueprintCallable, Category = "Network")
	void StartListener();
	
	/** Stop listening for UDP messages */
	UFUNCTION(BlueprintCallable, Category = "Network")
	void StopListener();
	
	/** Test the audio playback system with a sample file */
	UFUNCTION(BlueprintCallable, Category = "Audio")
	void TestAudioPlayback(const FString& TestAudioPath);

protected:
	/** Handle received UDP message (filename) */
	UFUNCTION()
	void OnUdpMessageReceived(const FString& Message);
	
	/** Import and play audio file */
	UFUNCTION(BlueprintCallable, Category = "Audio")
	void ImportAndPlayAudio(const FString& FilePath);
	
	/** Callback for when audio import is complete */
	UFUNCTION()
	void OnAudioImportComplete(URuntimeAudioImporterLibrary* Importer, UImportedSoundWave* ImportedSoundWave, ERuntimeImportStatus Status);
	
	/** Start lip sync for the current audio */
	UFUNCTION()
	void StartLipSync(UImportedSoundWave* SoundWave);
	
	/** Stop any currently playing audio and lip sync */
	UFUNCTION(BlueprintCallable, Category = "Audio")
	void StopCurrentAudio();

private:
	/** Currently playing sound wave */
	UPROPERTY()
	UImportedSoundWave* CurrentSoundWave;
	
	/** Audio importer library instance */
	UPROPERTY()
	URuntimeAudioImporterLibrary* AudioImporter;
	
	/** Flag to track if audio is currently playing */
	bool bIsAudioPlaying;
	
	/** Get the full path to an audio file */
	FString GetFullAudioPath(const FString& Filename);
};

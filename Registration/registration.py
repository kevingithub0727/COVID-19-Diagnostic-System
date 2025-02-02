import SimpleITK as sitk
import os


# Output info during transform
def command_iteration(method):
    if (method.GetOptimizerIteration() == 0):
        print("Estimated Scales: ", method.GetOptimizerScales())
    print(f"{method.GetOptimizerIteration():3} = {method.GetMetricValue():7.5f} : {method.GetOptimizerPosition()}")


def reg(fixedDirPath, movingDirPath, outputDirPath):
    # Set up image viewer with proper settings
    os.environ.setdefault("SITK_SHOW_EXTENSION", ".nii")

    # TODO: Make these files parameters for integration with the other system
    fixedDir = fixedDirPath
    movingDir = movingDirPath
    transformFile = "transform.txt"
    outputFile = outputDirPath

    # Use imageSeriesReader to read directory of DICOM images in as 3D images (nii format)
    reader = sitk.ImageSeriesReader()
    pixelType = sitk.sitkFloat32

    if fixedDir.split(".")[-1] == "nii":
        fixedImage = sitk.ReadImage(fixedDir, pixelType)
    else:
        print("Reading DICOM files from directory: ", fixedDir)
        dicom_names = reader.GetGDCMSeriesFileNames(fixedDir)
        reader.SetFileNames(dicom_names)
        sitk.WriteImage(reader.Execute(), "images/fixed.nii")
        fixedImage = sitk.ReadImage("images/fixed.nii", pixelType)


    print("Reading DICOM files from directory: ", movingDir)
    dicom_names = reader.GetGDCMSeriesFileNames(movingDir)
    reader.SetFileNames(dicom_names)
    sitk.WriteImage(reader.Execute(), "images/moving.nii")

    # Read in the newly generated 3D nii images
    movingImage = sitk.ReadImage("images/moving.nii", pixelType)

    numberOfBins = 24
    samplingPercentage = 0.10

    # Create our desired registration method
    regMethod = sitk.ImageRegistrationMethod()

    # Similarity metric
    regMethod.SetMetricAsMattesMutualInformation(numberOfBins)
    regMethod.SetMetricSamplingPercentage(samplingPercentage, sitk.sitkWallClock)
    regMethod.SetMetricSamplingStrategy(regMethod.RANDOM)

    # Optimizer
    regMethod.SetOptimizerAsRegularStepGradientDescent(1.0, .001, 200)

    # Transform
    regMethod.SetInitialTransform(sitk.CenteredTransformInitializer(fixedImage, movingImage, sitk.Euler3DTransform(), sitk.CenteredTransformInitializerFilter.GEOMETRY))
    # regMethod.SetInitialTransform(sitk.TranslationTransform(fixedImage.GetDimension()))

    regMethod.SetInterpolator(sitk.sitkLinear)

    # Attach our function for outputting information during registration
    regMethod.AddCommand(sitk.sitkIterationEvent, lambda: command_iteration(regMethod))

    # Generate the transform
    outTx = regMethod.Execute(fixedImage, movingImage)

    # Print transform along with registration method informatoin
    print("-------")
    print(f"Optimizer stop condition: {regMethod.GetOptimizerStopConditionDescription()}")
    print(f" Iteration: {regMethod.GetOptimizerIteration()}")
    print(f" Metric value: {regMethod.GetMetricValue()}")

    # Write the transform to the transform filw
    sitk.WriteTransform(outTx, transformFile)

    # If we aren't requested to not show the image
    if ("SITK_NOSHOW" not in os.environ):
        # Set up resampler
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(fixedImage)
        resampler.SetInterpolator(sitk.sitkLinear)
        resampler.SetDefaultPixelValue(100)
        resampler.SetTransform(outTx)

        # Run the resampler
        out = resampler.Execute(movingImage)
        simg1 = sitk.Cast(sitk.RescaleIntensity(fixedImage), sitk.sitkUInt8)
        simg2 = sitk.Cast(sitk.RescaleIntensity(out), sitk.sitkUInt8)

        # Create the final output
        # cimg = sitk.Compose(simg1, simg2, simg1 // 2. + simg2 // 2.)
        cimg = simg1 // 2. + simg2 // 2.

        # Save image as transformedImage in nii format
        writer = sitk.ImageFileWriter()
        writer.SetFileName(outputDirPath)
        writer.Execute(cimg)

        #Display the image using ImageJ
        sitk.Show(cimg, "Transformed_Image")